# Ideia

Ideia: simular uma gestora de ativos fictícia, com dados públicos reais e atualizados,
que vive só no GitHub.

A empresa tem:
- Um pipeline de dados: extração automatizada, preparo dos dados por área da empresa e
  dashboards específicos por tema/objetivo.
- Uma simulação em cima desses dados: um fluxo de decisão que gera novos processos
  (issues, PRs, mudanças de política), de forma que o que acontece hoje influencia o
  que acontece amanhã.

Cada dia útil, um agente Claude agendado (Scheduled task) executa a empresa.
Você decide como isso funciona no GitHub: arquitetura, ferramentas e etapas.

---

# Desenho proposto

> Empresa fictícia. Nenhuma saída deste repositório é recomendação de investimento.
> Nome provisório: **Capivara Asset** (a decidir).

## 1. Princípio central: fatos x intenções

A empresa é dividida em duas camadas que nunca se misturam:

| Camada | Quem executa | O que produz | Onde vive |
|---|---|---|---|
| **Determinística** (fatos) | GitHub Actions | dados extraídos, marts por área, cota dos fundos, eventos, dashboards | branch `dados` + GitHub Pages |
| **Decisória** (intenções) | Agente Claude agendado | issues, ordens, mudanças de política, PRs de código, diário | branch `main` (via PRs) |

- O agente **não calcula números**: lê o que o pipeline produziu e decide.
- O pipeline **não decide**: só executa o que está aprovado em `main` (ordens, políticas).
- O laço "hoje influencia amanhã" é fechado assim: decisão em `main` hoje → pipeline
  executa no fechamento → novos fatos amanhã → nova decisão.

Isso também resolve uma restrição prática: o ambiente cloud do agente não alcança as
fontes públicas (BCB, CVM, B3, Tesouro e IBGE foram bloqueados pelo proxy no teste),
enquanto os runners do GitHub Actions têm internet aberta. Toda extração fica no Actions.

## 2. O ciclo de um dia útil

Horários em BRT. Decisão no dia D usa dados até D-1 e executa no preço de fechamento de
D: sem look-ahead.

```
06:30  Actions · fechamento.yml (dados de D-1)
       extrair → dbt build (+ testes) → motor de simulação → eventos + briefing → Pages
08:45  Claude · rotina agendada (seg–sex)
       ler briefing/eventos → triagem → decisões → PR "Dia D" → merge se CI verde
D      ordens aprovadas aguardam o preço de fechamento de D
06:30  (D+1) Actions executa as ordens de D, remarca carteiras, gera novos eventos ...
```

### 2.1 `fechamento.yml` (GitHub Actions, cron seg–sex)
1. **Extrair** cada fonte com retry e idempotência (reprocessa os últimos N dias para
   pegar dados publicados com atraso, como o informe diário da CVM).
2. **Preparar** com dbt: `staging` → `intermediate` → `marts/<área>`; testes de qualidade e
   freshness falham o job.
3. **Simular** (`motor/`): executa ordens aprovadas, remarca posições a preço real, acumula
   taxas, gera captação/resgate dos cotistas simulados, checa limites e emite
   `eventos/AAAA-MM-DD.json` + `briefing.md` (resumo compacto para o agente).
4. **Publicar**: commit no branch `dados` e deploy dos dashboards no GitHub Pages.
5. **Falhou?** O job abre/atualiza uma issue `tipo:incidente` `area:dados`; o agente trata
   na manhã seguinte.

### 2.2 Rotina do agente (Claude Code, Scheduled task)
Uma sessão nova por disparo, com o repositório clonado e um prompt curto:
"Execute o dia útil conforme `OPERACAO.md`". O manual define os passos e os papéis
(skills em `.claude/skills/`):

0. **Abertura**: é dia útil (calendário B3)? O fechamento rodou? Se não, papel *Engenharia*
   diagnostica o incidente e opera em modo degradado (sem novas ordens com preço velho).
1. **Triagem**: cada evento vira issue nova ou comentário em issue aberta (dedupe por
   chave do evento), com rótulos de área e severidade.
2. **Gestão**: decide ordens dentro da política → `empresa/ordens/AAAA-MM-DD.yaml`.
3. **Risco/Compliance**: revisa desenquadramentos, escala o que está aberto há dias.
4. **Política**: se as condições pedirem (ciclo de Copom virou, quebras repetidas),
   abre PR alterando `empresa/politicas/*.yaml` com rótulo `comite`.
5. **Engenharia**: no máximo 1 item pequeno do backlog técnico por dia, em PR separado,
   com testes.
6. **Diário**: `empresa/diario/AAAA/MM-DD.md` com decisões, justificativa e links.
7. **Fechamento do agente**: ordens + diário vão num único PR "Dia AAAA-MM-DD"; merge
   automático se a CI passar. Um dia útil = um PR, histórico auditável.

Rituais com cadência própria:
- **Sexta**: comitê de investimentos → ata em `empresa/atas/` (performance vs benchmark,
  vs pares reais, vs gêmeo passivo; metas da semana seguinte).
- **1º dia útil do mês**: carta aos cotistas → GitHub Release `carta-AAAA-MM` com factsheet.

### 2.3 Governança (alçadas)
O agente opera com a identidade conectada ao GitHub, então não pode aprovar o próprio PR.
A governança usa CI + janela de objeção, com o João como "conselho":

| Tipo de PR | Gate | Merge |
|---|---|---|
| Dia (ordens + diário) | CI: compliance pré-trade, schema, testes | automático pelo agente |
| Política (`comite`) | CI + 2 dias úteis sem rótulo `veto` | agente, após a janela |
| Código | CI verde | **humano** |

Limites duros por dia (nº de issues/PRs abertos) evitam ruído e custo.

## 3. Estrutura do repositório

```
main
├── README.md               vitrine: o que é, links dos dashboards, estado de hoje
├── IDEIA.md                este documento
├── CLAUDE.md               regras para qualquer sessão Claude no repo
├── OPERACAO.md             manual do dia útil executado pelo agente
├── .claude/skills/         papéis: abertura, gestao, risco, compliance, comite, engenharia
├── .github/workflows/      fechamento.yml, ci.yml, pages.yml, mensal.yml
├── extracao/               um conector por fonte (Python)
├── transformacao/          projeto dbt (duckdb): staging/ intermediate/ marts/<área>/
├── motor/                  simulação: execução, cota, taxas, fluxo de cotistas, eventos
├── dashboards/             Evidence: uma página por área + home
└── empresa/
    ├── fundos/             mandato, benchmark, taxas de cada fundo fictício
    ├── politicas/          limites, alocação-alvo, regras de rebalanceamento (YAML)
    ├── ordens/             AAAA-MM-DD.yaml
    ├── diario/             AAAA/MM-DD.md
    └── atas/               comitês semanais

dados (branch órfão, só o Actions escreve)
├── curado/<fonte>/...parquet
├── estado/                 carteiras, cotas, cotistas, caixa
└── eventos/                AAAA-MM-DD.json + briefing.md
```

`main` guarda intenção e código (revisável); `dados` guarda fatos (append-only, sem ruído
no histórico de código). Arquivos brutos grandes, como o zip mensal da CVM, são filtrados
para o universo de interesse antes de persistir.

## 4. Fontes públicas (sem chave de API)

| Fonte | Dados | Uso |
|---|---|---|
| BCB SGS | Selic meta (432), CDI (12), IPCA (433), dólar (1) | macro, benchmark CDI |
| BCB Olinda | Focus (expectativas), PTAX | cenário, surpresas vs consenso |
| Tesouro Transparente | preços e taxas do Tesouro Direto | carteira de renda fixa, curva de juros |
| B3 COTAHIST | cotações diárias de ações e ETFs (BOVA11, IVVB11) | carteira de ações, benchmark |
| CVM Dados Abertos | informe diário de fundos (cota, PL, captação, resgate), cadastro | pares reais e calibração do fluxo de cotistas |
| IBGE SIDRA | IPCA aberto, PIB | research macro |

## 5. Áreas da empresa → marts → dashboards

| Área | Mart | Dashboard | Eventos típicos |
|---|---|---|---|
| Macro & Research | `marts/macro` | Cenário: juros, inflação, câmbio, Focus | Copom mudou a Selic, surpresa no IPCA |
| Gestão | `marts/gestao` | Carteiras, cota, atribuição de resultado | desvio da alocação-alvo |
| Risco | `marts/risco` | Vol, VaR, drawdown, concentração | limite de risco estourado |
| Compliance | `marts/compliance` | Enquadramento por regra da política | desenquadramento ativo/passivo |
| Comercial | `marts/comercial` | Captação, resgates, vs pares da CVM | resgate grande, perda de share |
| Dados | `marts/dados` | Freshness, volumes, testes, falhas | fonte atrasada, teste quebrou |

Fundos fictícios (começo com um, expando depois):
1. **Renda fixa**: títulos públicos (LFT, LTN, NTN-B). Benchmark: CDI.
2. **Ações**: universo do Ibovespa. Benchmark: BOVA11.
3. **Multimercado**: alocação entre RF, ações e dólar. Benchmark: CDI.

## 6. O que faz a simulação ser viva

- **Cota real**: decisões fictícias × preços reais. A Selic subiu de verdade? A carteira sente.
- **Cotistas simulados**: fluxo líquido = f(desempenho relativo aos pares reais em 1/3/12
  meses, drawdown, nível da Selic, ruído com semente = data). A sensibilidade é calibrada
  com captação/resgate reais do informe diário da CVM. Performance ruim vira resgate,
  que vira caixa a vender, que vira custo.
- **Receita da gestora**: taxas sobre o PL. PL cai, receita cai; numa fase posterior isso
  pode limitar o "orçamento" de engenharia do agente.
- **Dívida operacional**: incidentes e desenquadramentos abertos sobem de severidade com o
  tempo e exigem passos extras do agente.
- **Gêmeo passivo**: cada fundo tem um contrafactual que nunca rebalanceia. A diferença
  mede o valor que as decisões do agente adicionam (ou destroem).

## 7. Ferramentas

| Necessidade | Escolha | Por quê |
|---|---|---|
| Ambiente Python | Python 3.12 + uv | rápido e reprodutível no Actions |
| Extração | httpx + tenacity | retry/backoff explícitos |
| Armazenamento | Parquet + DuckDB | zero infraestrutura, cabe no Git |
| Transformação | dbt-core + dbt-duckdb | camadas, testes, docs de linhagem publicados |
| Simulação | pacote Python `motor` (pytest) | determinístico, testável, semente por data |
| Dashboards | Evidence (SQL + Markdown) → GitHub Pages | BI-as-code estático; alternativa: Quarto |
| Orquestração | GitHub Actions (cron + `workflow_dispatch`) | já mora no GitHub; backfill manual |
| Agente | Claude Code Scheduled task (rotina cloud) | opera via ferramentas GitHub (issues, PRs) |
| Processos | Issues, labels, PRs, Releases, Pages | a "intranet" da empresa |

Rótulos: `area:{macro,gestao,risco,compliance,comercial,dados}`,
`tipo:{alerta,tarefa,incidente,politica,ordem}`, `sev:{alta,media,baixa}`, `comite`, `veto`.

## 8. Etapas

| Fase | Entrega | Pronto quando |
|---|---|---|
| 0 | Limpeza do repo + este documento | este commit |
| 1 | Fundação de dados: BCB, Focus, Tesouro; dbt; dashboard macro e de dados; Pages | `fechamento.yml` roda sozinho por uma semana |
| 2 | Motor + fundo RF + políticas + ordens + CI de compliance pré-trade | dia simulado ponta a ponta via `workflow_dispatch` |
| 3 | Agente: `OPERACAO.md`, skills, rotina agendada, diário, governança | 5 dias úteis seguidos sem intervenção |
| 4 | Fundos de ações e multimercado, cotistas calibrados na CVM, gêmeo passivo, comitê, carta | primeira carta mensal publicada |
| 5 | Evolução: PRs de engenharia do agente, avaliação das decisões, retrospectivas | backlog técnico andando pelo agente |

## 9. Riscos e mitigação

| Risco | Mitigação |
|---|---|
| Fonte fora do ar ou mudou formato | contratos + testes dbt; incidente automático; modo degradado sem novas ordens |
| Agente inventa números | só lê marts/briefing; diário cita a origem; CI valida tudo que ele escreve |
| Ruído e custo de tokens | briefing pré-computado; teto diário de issues/PRs; dedupe por chave de evento |
| Cron do Actions atrasa ou é desativado após 60 dias sem atividade | horários com folga; commits diários mantêm o repo ativo |
| Parecer recomendação de investimento | aviso de empresa fictícia em todas as páginas; sem cotistas reais |
| Repositório crescer demais | dados no branch `dados`, só curados, brutos filtrados |

## 10. Decisões em aberto

1. Nome da gestora.
2. Começar só com o fundo de renda fixa (recomendado) ou já com os três?
3. O João quer papel ativo (conselho com `veto`) ou observador?
4. O agente pode fazer merge de PRs de código com CI verde, ou só humano?
5. Evidence ou Quarto para os dashboards?
