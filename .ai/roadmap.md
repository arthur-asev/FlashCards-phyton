# ROADMAP

## Fase 0 — Análise
- [x] analisar repositório;
- [x] validar stack;
- [x] validar requisitos;
- [x] criar `.ai/`;
- [x] definir arquitetura.

Resultado: a base existente é um monólito modular com FastAPI/Python 3.12, Vue 3/TypeScript/Vite, PostgreSQL 17 e Redis 7 via Docker Compose. Os contratos e a arquitetura das próximas fases já estão documentados em `.ai/`; persistência de domínio e processamento de jobs continuam fora desta fase.

## Fase 1 — Fundação
- [x] Docker Compose;
- [x] FastAPI;
- [x] Vue;
- [x] PostgreSQL;
- [x] Redis;
- [x] configuração;
- [x] health checks;
- [x] estrutura inicial.

Validação: `docker compose config --quiet`; testes de saúde do backend (4 aprovados); Ruff nos arquivos Python alterados; build de produção Vue/TypeScript; endpoints `/health` e `/ready` verificados com PostgreSQL e Redis ativos. `/health` verifica o processo; `/ready` verifica as duas dependências e retorna 503 se uma delas estiver indisponível.

## Fase 2 — Banco
- [x] SQLAlchemy;
- [x] Alembic;
- [x] entidades;
- [x] migrations;
- [x] seeds de desenvolvimento.

Validação: 7 testes backend aprovados; Ruff aprovado; migration inicial aplicada ao PostgreSQL e `alembic check` sem diferenças; seed executado duas vezes, mantendo um único subject, deck e card de exemplo.

## Fase 3 — Upload
- upload;
- validação;
- armazenamento;
- checksum;
- preview.

## Fase 4 — Planilhas
- XLSX;
- CSV;
- XLS;
- mapeamento;
- normalização;
- validação.

## Fase 5 — Exportação
- CSV;
- JSON;
- XLSX.

## Fase 6 — Flashcards
- CRUD de decks;
- CRUD de cards;
- matérias;
- assuntos;
- tags;
- filtros;
- busca.

## Fase 7 — IA
- AIProvider;
- MockProvider;
- integração com primeiro provedor;
- geração;
- validação;
- histórico.

## Fase 8 — Jobs
- Redis;
- worker;
- jobs;
- status;
- retry;
- tratamento de falhas.

## Fase 9 — Revisão
- reviews;
- cards pendentes;
- histórico;
- algoritmo isolado de repetição espaçada.

## Fase 10 — Frontend completo
- dashboard;
- upload;
- preview;
- mapeamento;
- decks;
- cards;
- geração por IA;
- revisão;
- estatísticas básicas.

## Fase 11 — Segurança
- autenticação;
- autorização;
- rate limiting;
- hardening de upload;
- gestão de secrets.

## Fase 12 — Qualidade
- unit tests;
- integration tests;
- E2E;
- lint;
- type checking;
- performance.

## Fase 13 — Observabilidade
- logs estruturados;
- métricas;
- request ID;
- monitoramento de jobs.

## Fase 14 — Deploy
- produção;
- banco;
- Redis;
- storage;
- CI/CD;
- backups;
- documentação operacional.

## Regra de avanço
Não avançar de fase com erros críticos ou dívida técnica bloqueadora.

Cada fase deve produzir:
- código;
- testes;
- documentação;
- validação.
