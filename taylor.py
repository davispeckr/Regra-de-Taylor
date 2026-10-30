"""
taylor.py
=========
Regra de Taylor e juro real ex-ante para o Brasil, com dados publicos do BCB.

    import taylor as tr
    dados = tr.montar_base()          # baixa SGS + Focus, devolve painel mensal
    res   = tr.regra(dados, r_neutro=5.0, a_pi=0.5, a_y=0.5)

--------------------------------------------------------------------------
NOTAS DE DESENHO
--------------------------------------------------------------------------
1. REGRA. Forma prospectiva, com a expectativa de inflacao 12 meses a frente
   no lugar da inflacao corrente:

       i*_t = r* + pi^e_t + a_pi (pi^e_t - pi*_t) + a_y h_t

   Parametros padrao de Taylor (1993): a_pi = a_y = 0,5. Nao e uma regra
   estimada nem uma recomendacao de Selic; e uma referencia normativa.

2. META 12 MESES A FRENTE. A expectativa do Focus cobre os 12 meses seguintes,
   que atravessam dois anos-calendario. A meta comparavel pondera as metas
   dos dois anos pela fracao de meses em cada um (SGS 13521).

3. HIATO. Duas medidas.
   (a) Filtro HP: desvio do log do PIB trimestral dessazonalizado (SGS 22109)
       em relacao a tendencia HP (lambda = 1600), em % do potencial. Usa a
       serie revisada; o HP bilateral sofre do problema de fim de amostra.
   (b) BCB em tempo real: estimativa do hiato publicada em cada Relatorio de
       Inflacao/RPM para o trimestre mais recente, coletada do texto dos
       relatorios (dados/bcb_hiato_relatorios.csv, com o trecho de origem).
       Disponivel desde o RI de mar/2021.

3b. JURO NEUTRO DO BCB. Valor usado nas projecoes do cenario de referencia,
   coletado de cada relatorio (dados/bcb_neutro_relatorios.csv). Disponivel
   desde o RI de dez/2020. Cada relatorio so e considerado disponivel a partir
   do primeiro dia do mes seguinte ao de referencia, para evitar look-ahead.

4. JURO REAL EX-ANTE. Mesma definicao do RPM: Selic esperada para os proximos
   12 meses (mediana do Focus por reuniao do Copom) descontada da expectativa
   de IPCA para o mesmo periodo. Entre reunioes vale a Selic meta vigente.
   Datas das reunioes: observadas no proprio Focus para as passadas e
   calendario oficial do BCB para as futuras (CALENDARIO_COPOM). Composicao
   em 252 dias uteis.

5. FONTES. api.bcb.gov.br (SGS) e olinda.bcb.gov.br (Focus). Sem credencial.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import time
import urllib.parse
import urllib.request

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.sparse.linalg import spsolve

SGS = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{c}/dados?formato=json&dataInicial={a}&dataFinal={b}"
OLINDA = "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/"

SELIC_META, META_INFL, PIB_SA = 432, 13521, 22109
INICIO = "2006-01-01"

DADOS = pathlib.Path(__file__).parent / "dados"


def relatorios_bcb() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Estimativas publicadas nos relatorios trimestrais do BCB (RI ate 2024,
    RPM desde 2025). Atualizar os CSVs a cada novo relatorio."""
    h = pd.read_csv(DADOS / "bcb_hiato_relatorios.csv")
    n = pd.read_csv(DADOS / "bcb_neutro_relatorios.csv")
    for d in (h, n):
        d["vigente_desde"] = (pd.PeriodIndex(d.mes_referencia, freq="M") + 1).to_timestamp()
    return h, n


def bcb_tempo_real(meses: pd.DatetimeIndex) -> pd.DataFrame:
    """Para cada mes, o hiato (trimestre mais recente estimado) e o juro neutro
    do ultimo relatorio do BCB ja disponivel naquele mes."""
    h, n = relatorios_bcb()
    out = []
    for m in meses:
        hv = h[h.vigente_desde <= m]
        nv = n[n.vigente_desde <= m]
        linha = {"hiato_bcb": np.nan, "hiato_bcb_trim": None, "neutro_bcb": np.nan, "bcb_relatorio": None}
        if len(hv):
            ult = hv[hv.mes_referencia == hv.mes_referencia.max()]
            r = ult.loc[ult.trimestre.idxmax()]
            linha.update(hiato_bcb=r.hiato, hiato_bcb_trim=r.trimestre,
                         bcb_relatorio=f"{r.relatorio} {r.mes_referencia}")
        if len(nv):
            r = nv.loc[nv.mes_referencia.idxmax()]
            linha.update(neutro_bcb=r.r_neutro)
            linha["bcb_relatorio"] = linha["bcb_relatorio"] or f"{r.relatorio} {r.mes_referencia}"
        out.append(linha)
    return pd.DataFrame(out, index=meses)


def neutro_bcb_atual() -> tuple[float, str]:
    _, n = relatorios_bcb()
    r = n.loc[n.mes_referencia.idxmax()]
    return float(r.r_neutro), f"{r.relatorio} {r.mes_referencia}"


# ------------------------------------------------------------------ download

def _get(url: str, tentativas: int = 4):
    for i in range(tentativas):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json",
                                                       "User-Agent": "regra-taylor/1.0"})
            return json.loads(urllib.request.urlopen(req, timeout=120).read().decode("utf-8"))
        except Exception:
            if i == tentativas - 1:
                raise
            time.sleep(3 * (i + 1))


def sgs(codigo: int, inicio: str = "2000-01-01") -> pd.Series:
    """Serie do SGS, paginada em blocos de 10 anos (limite da API para diarias)."""
    a = pd.Timestamp(inicio)
    fim = pd.Timestamp(dt.date.today())
    partes = []
    while a <= fim:
        b = min(a + pd.DateOffset(years=10) - pd.Timedelta(days=1), fim)
        url = SGS.format(c=codigo, a=a.strftime("%d/%m/%Y"), b=b.strftime("%d/%m/%Y"))
        partes += _get(url)
        a = b + pd.Timedelta(days=1)
    s = pd.Series({pd.to_datetime(r["data"], dayfirst=True): float(r["valor"]) for r in partes})
    return s.sort_index().rename(codigo)


def _olinda(recurso: str, filtro: str, campos: str, passo: int = 20000) -> pd.DataFrame:
    linhas, skip = [], 0
    while True:
        q = {"$filter": filtro, "$select": campos, "$format": "json",
             "$top": passo, "$skip": skip, "$orderby": "Data asc"}
        url = OLINDA + recurso + "?" + urllib.parse.urlencode(q, quote_via=urllib.parse.quote)
        v = _get(url)["value"]
        linhas += v
        if len(v) < passo:
            break
        skip += passo
    return pd.DataFrame(linhas)


def focus_ipca_12m(inicio: str = INICIO) -> pd.Series:
    """Mediana suavizada do IPCA 12 meses a frente, todos os respondentes."""
    d = _olinda("ExpectativasMercadoInflacao12Meses",
                f"Indicador eq 'IPCA' and Suavizada eq 'S' and baseCalculo eq 0 and Data ge '{inicio}'",
                "Data,Mediana")
    return d.assign(Data=pd.to_datetime(d.Data)).set_index("Data").Mediana.sort_index()


def focus_selic(inicio: str = INICIO) -> pd.DataFrame:
    """Mediana da Selic esperada por reuniao do Copom (Reuniao = 'Rk/AAAA')."""
    d = _olinda("ExpectativasMercadoSelic",
                f"baseCalculo eq 0 and Data ge '{inicio}'", "Data,Reuniao,Mediana")
    d["Data"] = pd.to_datetime(d.Data)
    return d


def focus_anuais(indicador: str, inicio: str = INICIO) -> pd.DataFrame:
    """Mediana das expectativas anuais (Selic de fim de ano ou IPCA do ano)."""
    d = _olinda("ExpectativasMercadoAnuais",
                f"Indicador eq '{indicador}' and baseCalculo eq 0 and Data ge '{inicio}'",
                "Data,DataReferencia,Mediana")
    d["Data"] = pd.to_datetime(d.Data)
    d["DataReferencia"] = d.DataReferencia.astype(int)
    return d


def neutro_focus(selic_a: pd.DataFrame, ipca_a: pd.DataFrame, datas,
                 horizonte: int = 3) -> pd.Series:
    """Juro real de longo prazo implicito no Focus: Selic e IPCA do ano t+h.
    Proxy de mercado para o juro neutro (a economia ja convergida)."""
    s = selic_a.set_index(["Data", "DataReferencia"]).Mediana
    p = ipca_a.set_index(["Data", "DataReferencia"]).Mediana
    out = {}
    for d in datas:
        k = (d, d.year + horizonte)
        out[d] = (((1 + s[k] / 100) / (1 + p[k] / 100) - 1) * 100
                  if k in s.index and k in p.index else np.nan)
    return pd.Series(out, name="neutro_focus")


# ------------------------------------------------------------------ calculos

# Calendario oficial das proximas reunioes (dia da decisao). Atualizar quando o
# BCB divulgar o calendario do ano seguinte (em geral em junho).
CALENDARIO_COPOM = {
    "R7/2026": "2026-11-04", "R8/2026": "2026-12-09",
    "R1/2027": "2027-01-27", "R2/2027": "2027-03-17", "R3/2027": "2027-04-28",
    "R4/2027": "2027-06-16", "R5/2027": "2027-08-04", "R6/2027": "2027-09-22",
    "R7/2027": "2027-10-27", "R8/2027": "2027-12-08",
}


def data_reuniao_aprox(codigo: str) -> pd.Timestamp:
    """Data aproximada da decisao: 8 reunioes por ano igualmente espacadas."""
    k, ano = codigo[1:].split("/")
    return pd.Timestamp(f"{ano}-01-01") + pd.Timedelta(days=round(26 + (int(k) - 1) * 365 / 8))


def datas_reunioes(focus: pd.DataFrame) -> pd.Series:
    """Data a partir da qual vale a decisao de cada reuniao.
    Reunioes passadas: dia seguinte a ultima pesquisa Focus em que a reuniao
    aparece (o Focus deixa de perguntar por ela quando a decisao sai; a nova
    meta passa a valer no dia seguinte, como na serie 432).
    Reunioes futuras: calendario oficial; na falta dele, aproximacao."""
    ult = focus.Data.max()
    datas = focus.groupby("Reuniao").Data.max() + pd.Timedelta(days=1)
    for c in datas.index[datas > ult]:
        datas[c] = (pd.Timestamp(CALENDARIO_COPOM[c]) + pd.Timedelta(days=1)
                    if c in CALENDARIO_COPOM else data_reuniao_aprox(c))
    return datas


def hp(y: np.ndarray, lamb: float = 1600.0) -> np.ndarray:
    """Tendencia do filtro Hodrick-Prescott (solucao exata por sistema esparso)."""
    n = len(y)
    D = sparse.diags([1.0, -2.0, 1.0], [0, 1, 2], shape=(n - 2, n))
    return spsolve((sparse.eye(n) + lamb * (D.T @ D)).tocsc(), y)


def hiato_hp(pib: pd.Series, lamb: float = 1600.0) -> pd.Series:
    ly = np.log(pib.to_numpy(float))
    h = 100 * (ly - hp(ly, lamb))
    return pd.Series(h, index=pd.PeriodIndex(pib.index, freq="Q"), name="hiato_hp")


def meta_12m(metas: pd.Series, meses: pd.DatetimeIndex) -> pd.Series:
    """Meta comparavel ao horizonte de 12 meses a frente de cada mes."""
    m = {d.year: v for d, v in metas.items()}
    out = []
    for t in meses:
        f_atual = (12 - t.month) / 12          # meses restantes do ano corrente
        a, b = m.get(t.year), m.get(t.year + 1, m.get(t.year))
        out.append(np.nan if a is None else f_atual * a + (1 - f_atual) * b)
    return pd.Series(out, index=meses, name="meta_12m")


def selic_esperada_12m(focus: pd.DataFrame, meta: pd.Series, datas,
                       efetivas: pd.Series) -> pd.Series:
    """Selic media composta esperada para os 252 dias uteis seguintes a cada data
    (convencao brasileira de base 252; feriados nao sao descontados)."""
    focus = focus.assign(efetiva=focus.Reuniao.map(efetivas))
    out = {}
    for d in datas:
        f = focus[(focus.Data == d) & (focus.efetiva > d)].sort_values("efetiva")
        dias = pd.bdate_range(d + pd.Timedelta(days=1), periods=252)
        trilha = pd.Series(meta.asof(d), index=dias, dtype=float)
        for _, r in f.iterrows():
            trilha[trilha.index >= r.efetiva] = r.Mediana
        out[d] = (np.prod((1 + trilha / 100) ** (1 / 252)) - 1) * 100
    return pd.Series(out, name="selic_esp_12m")


def montar_base(verbose: bool = True) -> pd.DataFrame:
    """Painel mensal: ultimo dado disponivel de cada mes."""
    log = print if verbose else (lambda *a, **k: None)
    log("SGS: Selic meta, metas de inflacao, PIB dessazonalizado")
    selic = sgs(SELIC_META, "2005-01-01")
    metas = sgs(META_INFL, "2000-01-01")
    pib = sgs(PIB_SA, "1996-01-01")
    log("Focus: IPCA 12 meses e Selic por reuniao")
    ipca_e = focus_ipca_12m()
    fsel = focus_selic()
    sel_a, ipca_a = focus_anuais("Selic"), focus_anuais("IPCA")

    hoje = pd.Timestamp(dt.date.today())
    ipca_e = ipca_e[ipca_e.index <= hoje]
    # data de referencia de cada mes = ultima pesquisa Focus do mes
    ref = ipca_e.groupby(ipca_e.index.to_period("M")).apply(lambda s: s.index.max())
    datas = pd.DatetimeIndex(ref.values)
    meses = ref.index.to_timestamp()

    log(f"Selic esperada 12m para {len(datas)} meses")
    efetivas = datas_reunioes(fsel)
    sel_esp = selic_esperada_12m(fsel[fsel.Data.isin(datas)], selic, datas, efetivas)

    h = hiato_hp(pib)
    df = pd.DataFrame({
        "data_focus": datas,
        "selic": [selic.asof(d) for d in datas],
        "ipca_e12": ipca_e.loc[datas].to_numpy(),
        "selic_e12": sel_esp.loc[datas].to_numpy(),
    }, index=meses)
    df["meta_12m"] = meta_12m(metas, meses)
    q = meses.to_period("Q")
    df["hiato_hp"] = h.reindex(q).to_numpy()
    df["hiato_trim_ref"] = [str(p) if p in h.index else str(h.index[-1]) for p in q]
    # meses sem PIB divulgado: carrega o ultimo trimestre e marca
    df["hiato_proj"] = df.hiato_hp.isna()
    df["hiato_hp"] = df.hiato_hp.ffill()
    df["juro_real_exante"] = ((1 + df.selic_e12 / 100) / (1 + df.ipca_e12 / 100) - 1) * 100
    df["neutro_focus"] = neutro_focus(sel_a, ipca_a, datas).to_numpy()
    df = df.join(bcb_tempo_real(meses))
    df.index.name = "mes"
    return df


def regra(df: pd.DataFrame, r_neutro=5.0, a_pi: float = 0.5,
          a_y: float = 0.5, hiato: str = "hiato_hp") -> pd.Series:
    """Selic implicita pela regra de Taylor (% a.a.). Formula nominal aditiva,
    padrao na literatura. r_neutro pode ser numero ou nome de coluna
    ("neutro_focus", "neutro_bcb"); hiato e nome de coluna ("hiato_hp", "hiato_bcb")."""
    r = df[r_neutro] if isinstance(r_neutro, str) else r_neutro
    return (r + df.ipca_e12 + a_pi * (df.ipca_e12 - df.meta_12m)
            + a_y * df[hiato]).rename("taylor")


# ------------------------------------------------------------- inferencia

def newey_west(x: pd.Series, defasagens: int | None = None) -> dict:
    """Media de uma serie temporal com erro-padrao de Newey-West (1987),
    nucleo de Bartlett. Defasagem padrao: floor(4 (T/100)^(2/9))."""
    x = x.dropna().to_numpy(float)
    T = len(x)
    L = int(np.floor(4 * (T / 100) ** (2 / 9))) if defasagens is None else defasagens
    u = x - x.mean()
    s = u @ u / T
    for l in range(1, L + 1):
        s += 2 * (1 - l / (L + 1)) * (u[l:] @ u[:-l]) / T
    ep = np.sqrt(s / T)
    return {"media": x.mean(), "ep": ep, "t": x.mean() / ep, "T": T, "L": L,
            "acima": float((x > 0).mean())}


ESPECIFICACOES = {
    "A": {"rotulo": "Neutro do Focus, hiato HP", "r_neutro": "neutro_focus", "hiato": "hiato_hp"},
    "B": {"rotulo": "Neutro e hiato do BCB em tempo real", "r_neutro": "neutro_bcb", "hiato": "hiato_bcb"},
    "C": {"rotulo": "Neutro fixo de 5%, hiato HP", "r_neutro": 5.0, "hiato": "hiato_hp"},
}


def resumo_desvios(df: pd.DataFrame, periodos: dict) -> pd.DataFrame:
    """Desvio medio Selic - regra por especificacao e periodo, com EP HAC."""
    linhas = []
    for k, e in ESPECIFICACOES.items():
        d = df.selic - regra(df, e["r_neutro"], hiato=e["hiato"])
        for nome, (a, b) in periodos.items():
            s = d.loc[a:b].dropna()
            if len(s) < 12:
                continue
            nw = newey_west(s)
            linhas.append({"especificacao": k, "descricao": e["rotulo"], "periodo": nome,
                           "inicio": s.index[0].strftime("%Y-%m"), "fim": s.index[-1].strftime("%Y-%m"),
                           "meses": nw["T"], "desvio_medio_pp": nw["media"], "ep_hac": nw["ep"],
                           "t": nw["t"], "frac_meses_acima": nw["acima"]})
    return pd.DataFrame(linhas)


if __name__ == "__main__":
    base = montar_base()
    base["taylor"] = regra(base)
    print(base.tail(14).round(2).to_string())
