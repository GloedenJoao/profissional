# Estudo de caso: um problema, três plataformas

**Período:** dez/2025 · **Repositórios:** `traking_income`, `traking_income2`, `traking_spending`, `Android_AppV4`

## O problema

Controle financeiro pessoal com regras que planilha resolve mal: salário antecipado para o dia útil anterior quando cai no fim de semana, vales creditados no **penúltimo dia útil**, fatura de cartão tratada como dívida e não como saldo, e projeção diária de saldo com transações futuras.

## Evolução em duas semanas

| Data | Projeto | Stack | Marco |
|---|---|---|---|
| 01/dez | `traking_income` | Flask + SQLite + pytest | CRUD de lançamentos de holerite com consolidação mensal recalculada automaticamente. |
| 01–02/dez | `traking_income2` | FastAPI + PyMuPDF + Plotly | **Parser de PDF** de holerite; login e cadastro; uploads isolados por usuário; impersonação de admin para suporte. 46 commits em dois dias. |
| 09–13/dez | `traking_spending` | FastAPI + SQLAlchemy + Docker + **Fly.io** | Motor de simulação diária com regras de dia útil; eventos futuros persistidos; dashboard com faixas e variação diária; **deploy em produção** no Fly.io. |
| 14/dez | `Android_AppV4` ("Simule Gastos") | Kotlin + Jetpack Compose | O mesmo motor portado para Android nativo: abas, simulação por intervalos de datas, transferências, dashboard. 52 commits num dia, corrigindo build Gradle, depreciações do Compose e UX. |

## O que esse ciclo mostra

- **Regras de negócio primeiro, plataforma depois.** O motor de simulação (dia útil, penúltimo dia útil, fatura negativa) foi documentado no README e no `AGENTS.md` e reimplementado igual em Python e Kotlin.
- **Levar até produção.** `traking_spending` saiu do localhost com Dockerfile e deploy no Fly.io.
- **Aprender uma stack nova em um dia com agentes.** O app Android partiu de zero conhecimento de Compose. As tentativas V1–V3 do mesmo dia foram descartadas até a V4 compilar e funcionar.

## Por que não está em destaque

São ferramentas pessoais: os dados e parte do código envolvem informação financeira própria. O que vale para o portfólio é o **processo**, e ele está descrito aqui.
