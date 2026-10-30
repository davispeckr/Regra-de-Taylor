# Regra de Taylor – Brasil

Painel e código para comparar a taxa Selic com a taxa implícita por uma regra de Taylor prospectiva e para medir o grau de aperto monetário pelo juro real ex-ante em relação ao juro neutro. Todos os dados são públicos e vêm do Banco Central do Brasil. A série é mensal e começa em janeiro de 2006.

**Dashboard:** https://davispeckr.github.io/Regra-de-Taylor/

Autor: Davi Speck Ramos (UDESC/ESAG).

---

## 1. Motivação

A regra de Taylor (Taylor, 1993) descreve a taxa básica de juros como função do juro real de equilíbrio, do desvio da inflação em relação à meta e do hiato do produto. Na literatura e na prática de bancos centrais, ela serve como referência normativa: indica onde estaria a taxa básica se a autoridade monetária reagisse à inflação e à atividade com pesos fixos e conhecidos. A distância entre a taxa efetiva e a taxa da regra resume, em um número, se a política está mais apertada ou mais frouxa do que essa referência.

Este repositório constrói essa comparação para o Brasil com três escolhas de desenho:

1. **Forma prospectiva.** A inflação entra pela expectativa para os próximos 12 meses, e não pela inflação corrente, seguindo a tradição de regras *forward-looking* (Clarida, Galí e Gertler, 2000) e a forma como o Copom comunica suas decisões.
2. **Transparência sobre os não observáveis.** O juro neutro e o hiato do produto não são observáveis. Em vez de fixar uma única estimativa, o painel oferece alternativas documentadas e mostra a faixa de resultados que elas produzem.
3. **Dados em tempo real do próprio BCB.** Além de medidas revisadas, o painel usa o hiato e o juro neutro que o Banco Central publicava em cada relatório trimestral, coletados do texto dos relatórios. Assim, cada decisão pode ser comparada com a regra calculada com a informação e as premissas que o Copom tinha na época (Orphanides, 2001).

A pergunta de pesquisa que orienta o projeto é se, em média, a política monetária brasileira foi mais apertada (*hawkish*) ou mais frouxa (*dovish*) do que uma regra de referência, e quanto essa conclusão depende das premissas sobre os não observáveis. A seção 6 traz uma primeira evidência descritiva.

## 2. Especificação

A taxa implícita pela regra no mês $`t`$ é

```math
i^{T}_{t} = r^{*}_{t} + \pi^{e}_{t} + \alpha_{\pi}\left(\pi^{e}_{t} - \pi^{*}_{t}\right) + \alpha_{y}\, h_{t}
```

em que:

| Símbolo | Definição |
| --- | --- |
| $`i^{T}_{t}`$ | Selic implícita pela regra, em % a.a. |
| $`r^{*}_{t}`$ | Juro real neutro, em % a.a. |
| $`\pi^{e}_{t}`$ | Mediana suavizada do Focus para o IPCA dos 12 meses seguintes |
| $`\pi^{*}_{t}`$ | Meta de inflação comparável ao mesmo horizonte (seção 3.2) |
| $`h_{t}`$ | Hiato do produto, em % do produto potencial (seção 3.3) |
| $`\alpha_{\pi}, \alpha_{y}`$ | Pesos de reação; padrão $`\alpha_{\pi} = \alpha_{y}`$ = 0,5, como em Taylor (1993) |

A formulação é aditiva e nominal: a soma $`r^{*} + \pi^{e}`$ aproxima a taxa nominal neutra, e os dois termos seguintes capturam a reação ao desvio de inflação e ao hiato. Com $`\alpha_{\pi} > 0`$, a regra satisfaz o princípio de Taylor: a taxa nominal responde mais do que proporcionalmente à inflação esperada, com coeficiente $`1 + \alpha_{\pi}`$.

A regra não é estimada. Os pesos são parâmetros normativos e o painel permite alterá-los ($`\alpha_{\pi}`$ ∈ {0,5; 1,0; 1,5} e $`\alpha_{y}`$ ∈ {0,5; 1,0}). O resultado, portanto, não é uma previsão da decisão do Copom nem uma função de reação estimada do Banco Central.

### 2.1 Juro real ex-ante

O grau de aperto também é medido pelo juro real ex-ante, com a mesma definição usada pelo Banco Central no Relatório de Política Monetária (RPM):

```math
r^{\,ex\text{-}ante}_{t} = \frac{1 + \bar{i}^{\,e}_{t,\,t+12}}{1 + \pi^{e}_{t}} - 1
```

em que $`\bar{i}^{\,e}_{t,\,t+12}`$ é a Selic média composta esperada para os 12 meses seguintes. A distância $`r^{\,ex\text{-}ante}_{t} - r^{*}_{t}`$ indica postura contracionista quando positiva.

## 3. Construção das variáveis

### 3.1 Frequência e data de referência

O painel é mensal. Para cada mês, a data de referência é a da última pesquisa Focus disponível no mês, e as demais variáveis são lidas nessa data. Isso mantém a comparação no mesmo conjunto de informação dos agentes, sem misturar dados divulgados depois.

### 3.2 Meta comparável

A expectativa de 12 meses à frente atravessa dois anos-calendário. A meta comparável pondera as metas dos dois anos pela fração de meses em cada um:

```math
\pi^{*}_{t} = \frac{12 - m_t}{12}\,\pi^{*}_{a(t)} + \frac{m_t}{12}\,\pi^{*}_{a(t)+1}
```

em que $`m_t`$ é o mês do calendário e $`a(t)`$ é o ano. Desde 2025, sob a meta contínua, $`\pi^{*}_{t}`$ = 3%.

### 3.3 Hiato do produto

São oferecidas duas medidas.

**Filtro HP.** O hiato é o desvio percentual do log do PIB trimestral dessazonalizado em relação à tendência do filtro de Hodrick e Prescott (1997), com $`\lambda`$ = 1.600:

```math
h_{q} = 100\left(\ln Y_{q} - \tau_{q}\right)
```

```math
\tau = \arg\min_{\tau} \sum_{q}\left(\ln Y_{q} - \tau_{q}\right)^{2} + \lambda \sum_{q}\left(\Delta^{2}\tau_{q}\right)^{2}
```

O valor trimestral é atribuído aos três meses do trimestre. Meses posteriores ao último PIB divulgado repetem o último trimestre disponível.

**Estimativa do BCB.** Estimativa do hiato para o trimestre mais recente publicada em cada Relatório de Inflação (RI, até 2024) e Relatório de Política Monetária (RPM, desde 2025). A medida combina várias metodologias com o julgamento do Copom e não é revisada depois: é o que o Banco Central estimava na época. O texto dos relatórios traz o valor desde o RI de março de 2021; antes disso, o hiato aparece só em gráficos, e a opção fica sem dado.

A versão HP é reprodutível e cobre toda a amostra, mas usa dados revisados e sofre do problema de fim de amostra: o filtro bilateral revisa as últimas observações quando chegam dados novos (Orphanides, 2001; Hamilton, 2018). As duas medidas podem divergir bastante. Em abril de 2021, por exemplo, o HP indicava −0,6% e o BCB estimava −3,2%.

### 3.4 Juro neutro

São oferecidas quatro opções.

**BCB hoje.** Valor usado nas projeções do cenário de referência no relatório mais recente, aplicado a toda a amostra.

**BCB na época.** Valor que o Banco Central usava nas projeções em cada momento, coletado de cada relatório desde o RI de dezembro de 2020, quando passou a ser divulgado: 3,0% (dez/2020 a set/2021), 3,5% (dez/2021 e mar/2022), 4,0% (jun/2022 a mar/2023), 4,5% (jun/2023 a mar/2024), 4,75% (jun e set/2024) e 5,0% (desde dez/2024).

**Mercado.** Juro real de longo prazo implícito no Focus, a partir da Selic de fim de ano e do IPCA esperados para o terceiro ano à frente, quando a economia já teria convergido ao equilíbrio:

```math
r^{*,\mathrm{Focus}}_{t} = \frac{1 + i^{e}_{t,\,a+3}}{1 + \pi^{e}_{t,\,a+3}} - 1
```

Essa medida reflete as expectativas dos participantes do Focus e pode incorporar prêmios de risco. É uma proxy de mercado, não uma estimativa estrutural no sentido de Laubach e Williams (2003).

**Personalizado.** Qualquer valor fixo entre 2% e 9% a.a.

### 3.5 Coleta dos relatórios do BCB

Os valores de hiato e juro neutro foram extraídos do texto de 32 relatórios trimestrais (dezembro de 2018 a setembro de 2026) e gravados com o trecho de origem em `dados/bcb_hiato_relatorios.csv` e `dados/bcb_neutro_relatorios.csv`. Uma verificação automática confirma que cada trecho aparece no relatório correspondente e que o número gravado consta do trecho (71 de 71 valores).

Para evitar *look-ahead*, cada relatório só é considerado disponível a partir do primeiro dia do mês seguinte ao de referência. Em cada mês, o hiato em tempo real é a estimativa para o trimestre mais recente no último relatório disponível, e o juro neutro é o valor desse mesmo relatório.

### 3.6 Selic esperada para 12 meses

A trajetória esperada é montada com a mediana do Focus para cada reunião do Copom. Entre a data de referência e a primeira reunião vale a Selic meta vigente; depois de cada reunião vale a mediana esperada para ela. A taxa média é a composição dessa trajetória ao longo dos 252 dias úteis seguintes, convenção de base 252 do mercado brasileiro:

```math
\bar{i}^{\,e}_{t,\,t+12} = \left[\prod_{d=1}^{252}\left(1 + i_{d}\right)^{1/252}\right] - 1
```

Para reuniões já realizadas, a data da decisão é inferida do próprio Focus: a pesquisa deixa de perguntar por uma reunião quando a decisão sai, e a nova meta passa a valer no dia seguinte, como na série 432. Para as reuniões futuras, usa-se o calendário oficial do Copom (`CALENDARIO_COPOM`, em `taylor.py`). Feriados não são descontados da contagem de dias úteis.

**Validação.** Um recálculo independente, escrito sem reaproveitar o código do painel (filtro HP via `statsmodels`), reproduz a regra, o hiato, o neutro do Focus e a meta comparável sem diferença, e o juro real ex-ante com diferença máxima de 0,007 ponto percentual. A média do juro real ex-ante no 3º trimestre de 2025 é 9,73%, próxima do pico de 9,6% informado pelo RPM de setembro de 2026, que usa médias trimestrais e a pesquisa Focus da semana anterior a cada reunião.

## 4. Dados

| Série | Fonte | Código ou recurso |
| --- | --- | --- |
| Selic meta | BCB/SGS | 432 |
| Meta de inflação | BCB/SGS | 13521 |
| PIB trimestral dessazonalizado (1995 = 100) | BCB/SGS | 22109 |
| IPCA esperado, 12 meses à frente | Focus, API Olinda | `ExpectativasMercadoInflacao12Meses` (IPCA, suavizada, todos os respondentes) |
| Selic esperada por reunião do Copom | Focus, API Olinda | `ExpectativasMercadoSelic` |
| Selic e IPCA anuais esperados | Focus, API Olinda | `ExpectativasMercadoAnuais` |
| Juro neutro das projeções e hiato estimado | Relatórios de Inflação e de Política Monetária | Edições trimestrais desde dez/2020 (neutro) e mar/2021 (hiato) |

Todas as fontes são públicas e não exigem credencial. A série começa em janeiro de 2006, primeiro ano com oito reuniões do Copom e expectativas do Focus por reunião.

## 5. Leitura de outubro de 2026

Resultados com a pesquisa Focus de 23/10/2026 e o RPM de setembro de 2026 ($`r^{*}_{BCB}`$ = 5,00%; hiato de 0,4% no 3º trimestre de 2026):

| | Neutro BCB (5,00%) | Neutro Focus (6,28%) |
| --- | --- | --- |
| Hiato HP (−0,42%) | 10,09% | 11,37% |
| Hiato BCB (+0,40%) | 10,50% | 11,78% |

Com a Selic meta em 13,75%, a política monetária estava entre 1,97 e 3,66 pontos percentuais acima da regra. O juro real ex-ante, de 7,82%, superava o neutro em 1,54 a 2,82 pontos percentuais. A desancoragem das expectativas (IPCA esperado de 4,53% contra meta de 3%) acrescentava 0,77 ponto à regra. Esses números mudam a cada atualização; o painel mostra sempre a leitura mais recente.

## 6. Evidência descritiva: a política foi mais apertada ou mais frouxa do que a regra?

A tabela mostra a média mensal de $`d_t = i_t - i^{T}_{t}`$ (Selic meta menos regra, pesos 0,5 e 0,5) em três especificações:

- **A.** Neutro implícito no Focus e hiato HP: cobre toda a amostra, com premissas de mercado.
- **B.** Neutro e hiato do BCB em tempo real: a régua do próprio Banco Central na data de cada decisão, disponível desde abril de 2021.
- **C.** Neutro fixo de 5% e hiato HP: referência simples, comparável no tempo.

Os erros-padrão são de Newey e West (1987), com núcleo de Bartlett e defasagem $`L = \lfloor 4(T/100)^{2/9} \rfloor`$, porque o desvio é muito persistente. A tabela é regenerada a cada execução do `build.py`.

<!-- RESUMO:INICIO -->
| Especificação | Período | Meses | Desvio médio (pp) | EP HAC | t | Meses acima da regra |
| --- | --- | --- | --- | --- | --- | --- |
| A. Neutro do Focus, hiato HP | 2006-01 a 2026-10 | 250 | 0,76 | 0,35 | 2,1 | 56% |
| B. Neutro e hiato do BCB em tempo real | 2021-04 a 2026-10 | 67 | 2,88 | 0,48 | 6,0 | 88% |
| C. Neutro fixo de 5%, hiato HP | 2006-01 a 2026-10 | 250 | 0,49 | 0,46 | 1,1 | 58% |
<!-- RESUMO:FIM -->

**Leitura preliminar.** Na amostra de 2006 a 2026, o desvio médio é positivo nas especificações A e C, mas modesto e sensível à premissa de juro neutro; com neutro fixo de 5%, não é estatisticamente diferente de zero. Pela régua do próprio BCB em tempo real (especificação B), a Selic ficou acima da regra padrão em quase todos os meses desde 2021.

Esse resultado não basta para classificar o BC como *hawkish*. Um desvio positivo persistente é compatível com pelo menos três explicações:
1. **Reação mais forte que a de Taylor.** Um $`\alpha_{\pi}`$ efetivo maior que 0,5, como esperado quando as expectativas se desancoram.
2. **Suavização da taxa de juros.** A Selic se ajusta gradualmente, e a regra estática não tem termo de inércia.
3. **Fatores fora da regra.** Balanço de riscos, câmbio, choques de oferta e prêmio fiscal.

Separar essas explicações exige estimar uma função de reação com suavização (Clarida, Galí e Gertler, 2000).

## 7. Limitações

1. **Variáveis não observáveis.** O resultado depende do juro neutro e do hiato. A faixa apresentada cobre apenas as alternativas oferecidas, não toda a incerteza sobre essas variáveis.
2. **Dados revisados na especificação HP.** O PIB e o hiato pelo filtro HP são revisados. A especificação B usa dados em tempo real, mas só existe desde 2021.
3. **Cobertura das séries do BCB.** O neutro é divulgado desde dez/2020 e o hiato, no texto, desde mar/2021. Para períodos anteriores, a coleta exigiria extrair valores de gráficos.
4. **Data de disponibilidade.** A regra de "mês seguinte ao de referência" é conservadora e pode atrasar em algumas semanas a incorporação de um relatório.
5. **Natureza normativa.** A regra não incorpora outros determinantes das decisões do Copom.
6. **Inferência com séries persistentes.** O desvio é muito autocorrelacionado, e o erro-padrão HAC é impreciso em amostras curtas, como a da especificação B.

## 8. Reprodução

```bash
pip install -r requirements.txt
python build.py            # baixa SGS e Focus, recalcula e gera docs/index.html
python build.py --cache    # reusa docs/base.csv; relê só os dados dos relatórios do BCB
```

O pipeline aborta se alguma das séries centrais tiver lacunas. Um workflow do GitHub Actions roda toda segunda-feira, dia de divulgação do Focus, e só faz commit quando os dados mudam. A cada novo relatório trimestral do BCB, acrescente as linhas correspondentes em `dados/bcb_hiato_relatorios.csv` e `dados/bcb_neutro_relatorios.csv`, com o trecho de origem. Atualize `CALENDARIO_COPOM`, em `taylor.py`, quando o calendário do ano seguinte for divulgado.

```
taylor.py                  ingestão (SGS, Focus) e cálculos
build.py                   pipeline e geração do HTML
template/page.html         página do dashboard (dados injetados no build)
docs/index.html            dashboard publicado via GitHub Pages
docs/base.csv              painel mensal com todas as séries usadas
docs/resumo.csv            desvio médio Selic − regra por especificação e período
dados/                     hiato e juro neutro coletados dos relatórios do BCB
.github/workflows/         atualização semanal automática
```

## Referências

Banco Central do Brasil (2018–2024). *Relatório de Inflação*, edições trimestrais de dezembro de 2018 a dezembro de 2024.

Banco Central do Brasil (2025–2026). *Relatório de Política Monetária*, edições trimestrais de março de 2025 a setembro de 2026.

Clarida, R., Galí, J. e Gertler, M. (2000). Monetary policy rules and macroeconomic stability: evidence and some theory. *Quarterly Journal of Economics*, 115(1), 147–180.

Hamilton, J. D. (2018). Why you should never use the Hodrick-Prescott filter. *Review of Economics and Statistics*, 100(5), 831–843.

Hodrick, R. J. e Prescott, E. C. (1997). Postwar U.S. business cycles: an empirical investigation. *Journal of Money, Credit and Banking*, 29(1), 1–16.

Laubach, T. e Williams, J. C. (2003). Measuring the natural rate of interest. *Review of Economics and Statistics*, 85(4), 1063–1070.

Newey, W. K. e West, K. D. (1987). A simple, positive semi-definite, heteroskedasticity and autocorrelation consistent covariance matrix. *Econometrica*, 55(3), 703–708.

Orphanides, A. (2001). Monetary policy rules based on real-time data. *American Economic Review*, 91(4), 964–985.

Taylor, J. B. (1993). Discretion versus policy rules in practice. *Carnegie-Rochester Conference Series on Public Policy*, 39, 195–214.
