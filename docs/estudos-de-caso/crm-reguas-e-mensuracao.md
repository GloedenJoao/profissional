# Estudo de caso: de réguas de CRM a mensuração causal

**Período:** set/2025 → set/2026 · **Repositórios:** `crm`, `crm_conceito`, `regua_uml` → [`projetos/02-mensuracao-crm`](../../projetos/02-mensuracao-crm)

## Contexto profissional

De 2023 a 2025 trabalhei com CRM: concebi, automatizei e medi réguas de comunicação e campanhas sazonais de consignado, cartão de crédito e financiamento de veículos. Em set/2025 passei para inteligência de mercado, onde meço e atribuo a aquisição de clientes PJ entre canais. Os projetos pessoais acompanharam essa mudança de pergunta, de **"o que a régua dispara?"** para **"o que a régua causa?"**.

## Linha do tempo

### `crm`: case técnico de CRM (set/2025)
- ETL de uma planilha para SQLite (`etl.py`), com normalização de tipos pt-BR (vírgula decimal, datas).
- As perguntas de negócio foram respondidas **100% em SQL** e executadas via Python (`query_runner.py`).
- Webapp de apresentação com as respostas, uma proposta de régua de comunicação e um sandbox SQL.
- *Repositório privado: contém a base do case, que não é minha para publicar.*

### `crm_conceito`: POC de indicadores (set/2025)
- Gerador de **base simulada de 10 mil clientes** com distribuições controladas (segmento, datas de abertura, flags de produto).
- ETL para SQLite e webapp FastAPI com cards e gráfico filtráveis.
- Aprendizado: simular dados permite construir e demonstrar sem expor nada real, e essa técnica virou padrão nos meus projetos seguintes.

### `regua_uml`: modelagem de réguas (out/2025)
- Flask + SQLAlchemy modelando **jornadas → temas → regras → dias de comunicação**, com temas alternativos (auto-relacionamento) e exclusão em cascata.
- **Diagrama gerado automaticamente em Mermaid** a partir do banco, com jornadas coloridas e legenda. A régua documentada é a mesma que está cadastrada.
- 25 commits em uma semana: primeiro o modelo de dados, depois o diagrama, depois a UX.

### `mensuracao-crm`: incrementalidade x atribuição (set/2026)
- Base sintética com **efeito causal conhecido** e grupo de controle.
- SQL de lift com IC 95%, last-touch com lookback e desempate por prioridade de canal, curva acumulada com window functions.
- **Cálculo de poder:** qual holdout detecta o efeito que justifica a campanha.
- Resultado principal: o last-touch superestima o CRM em 2,5x a 5,7x frente ao incremental medido.

## O que mudou

| | 2025 | 2026 |
|---|---|---|
| Pergunta | Quantos clientes, quantas comunicações, qual régua | Quantas conversões a campanha **causou** |
| Técnica | ETL + agregação SQL + UI | Desenho experimental + window functions + estatística |
| Validação | Visual | Testes com resposta conhecida (base montada à mão e simulação com efeito real configurado) |
