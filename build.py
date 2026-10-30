#!/usr/bin/env python3
"""
build.py — pipeline do dashboard Regra de Taylor Brasil.

    python build.py            # baixa SGS + Focus, recalcula e gera docs/index.html
    python build.py --cache    # reusa docs/base.csv (so as series do BCB sao relidas de dados/)

Saidas em docs/:
    index.html     dashboard (arquivo unico, dados embutidos)
    base.csv       painel mensal com todas as series usadas
    resumo.csv     desvio medio Selic - regra por especificacao e periodo (EP HAC)
    fragment.html  mesmo conteudo sem o esqueleto <html>, para previa

Atualiza tambem a tabela de resumo do README, entre os marcadores RESUMO.
Falha se o painel vier vazio ou com buracos nas series centrais.
"""
import argparse
import datetime as dt
import json
import pathlib
import re
import sys

import pandas as pd

RAIZ = pathlib.Path(__file__).parent
sys.path.insert(0, str(RAIZ))
import taylor as tr  # noqa: E402

DOCS, TEMPLATE, README = RAIZ / "docs", RAIZ / "template" / "page.html", RAIZ / "README.md"
CENTRAIS = ["selic", "ipca_e12", "meta_12m", "hiato_hp", "juro_real_exante", "neutro_focus", "selic_e12"]
COLS_BCB = ["hiato_bcb", "hiato_bcb_trim", "neutro_bcb", "bcb_relatorio"]

PERIODOS = {"Amostra completa": ("2006-01", "2100-12")}


def tabela_md(res: pd.DataFrame) -> str:
    f = lambda v, d=2: f"{v:.{d}f}".replace(".", ",")
    linhas = ["| Especificação | Período | Meses | Desvio médio (pp) | EP HAC | t | Meses acima da regra |",
              "| --- | --- | --- | --- | --- | --- | --- |"]
    for _, r in res.iterrows():
        linhas.append(f"| {r.especificacao}. {r.descricao} | {r.inicio} a {r.fim} | {r.meses} | "
                      f"{f(r.desvio_medio_pp)} | {f(r.ep_hac)} | {f(r.t, 1)} | {f(100 * r.frac_meses_acima, 0)}% |")
    return "\n".join(linhas)


def main(cache: bool = False) -> None:
    DOCS.mkdir(exist_ok=True)
    csv = DOCS / "base.csv"
    if cache and csv.exists():
        base = pd.read_csv(csv, index_col="mes", parse_dates=["mes", "data_focus"])
        base = base.drop(columns=[c for c in COLS_BCB if c in base]).join(tr.bcb_tempo_real(base.index))
    else:
        base = tr.montar_base()
    base.to_csv(csv)

    if base.empty or base[CENTRAIS].isna().any().any():
        faltas = base[CENTRAIS].isna().sum()
        raise SystemExit(f"ABORTADO: series com lacunas\n{faltas[faltas > 0]}")

    res = tr.resumo_desvios(base, PERIODOS)
    res.round(4).to_csv(DOCS / "resumo.csv", index=False)
    if README.exists():
        txt = README.read_text(encoding="utf-8")
        bloco = f"<!-- RESUMO:INICIO -->\n{tabela_md(res)}\n<!-- RESUMO:FIM -->"
        txt = re.sub(r"<!-- RESUMO:INICIO -->.*?<!-- RESUMO:FIM -->", lambda _: bloco, txt, flags=re.S)
        README.write_text(txt, encoding="utf-8")

    r_atual, rel_atual = tr.neutro_bcb_atual()
    r2 = lambda s: [None if pd.isna(v) else round(float(v), 3) for v in s]
    pay = {
        "meses": [d.strftime("%Y-%m") for d in base.index],
        "data_focus": [pd.Timestamp(d).strftime("%Y-%m-%d") for d in base.data_focus],
        "selic": r2(base.selic), "ipca_e12": r2(base.ipca_e12), "meta_12m": r2(base.meta_12m),
        "hiato_hp": r2(base.hiato_hp), "hiato_bcb": r2(base.hiato_bcb),
        "hiato_bcb_trim": [None if pd.isna(v) else str(v) for v in base.hiato_bcb_trim],
        "neutro_bcb": r2(base.neutro_bcb), "bcb_relatorio": [None if pd.isna(v) else str(v) for v in base.bcb_relatorio],
        "juro_real": r2(base.juro_real_exante), "selic_e12": r2(base.selic_e12),
        "neutro_focus": r2(base.neutro_focus),
        "r_bcb": r_atual, "rel_neutro": rel_atual,
        "resumo": [{k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}
                   for r in res.to_dict("records")],
        "gerado": dt.date.today().isoformat(),
    }
    frag = TEMPLATE.read_text(encoding="utf-8").replace("/*__DATA__*/", json.dumps(pay, separators=(",", ":")))
    (DOCS / "fragment.html").write_text(frag, encoding="utf-8")
    html = ('<!DOCTYPE html>\n<html lang="pt-BR">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            + frag.replace("\n<div class=\"wrap\">", "\n</head>\n<body>\n<div class=\"wrap\">", 1)
            + "\n</body>\n</html>\n")
    (DOCS / "index.html").write_text(html, encoding="utf-8")

    t = tr.regra(base, r_atual).iloc[-1]
    print(f"OK · {pay['meses'][0]} a {pay['meses'][-1]} · Selic {base.selic.iloc[-1]:.2f} · "
          f"regra (r*={r_atual}, HP) {t:.2f} · {len(html)/1024:.0f} KB")
    print(res[["especificacao", "periodo", "meses", "desvio_medio_pp", "ep_hac", "t", "frac_meses_acima"]]
          .round(2).to_string(index=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", action="store_true", help="reusa docs/base.csv")
    main(**vars(ap.parse_args()))
