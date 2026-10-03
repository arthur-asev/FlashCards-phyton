# Flashcard Platform

Plataforma web para importação/conversão de planilhas e criação/organização de flashcards.

## Stack
- Backend: Python + FastAPI
- Frontend: Vue 3 + TypeScript + Vite
- Database: PostgreSQL
- Queue/cache: Redis
- Workers: processo Python inicial
- Docker Compose

## Inicialização

1. Copie `.env.example` para `.env`.
2. Execute:

```bash
docker compose up -d --build
```

3. Acesse:
- Frontend: http://localhost:5173
- API: http://localhost:8000
- Swagger: http://localhost:8000/docs

## Desenvolvimento

Backend:

```bash
docker compose exec --workdir /app backend python -m pytest /app/tests
```

Frontend:

```bash
docker compose exec --workdir /app frontend npm run build
```

## Regra para Codex

Leia primeiro:
- `.ai/system-prompt.md`
- `.ai/requirements.md`
- `.ai/architecture.md`
- `.ai/database.md`
- `.ai/api.md`
- `.ai/testing.md`
- `.ai/coding-rules.md`
- `.ai/roadmap.md`

A primeira tarefa é análise do repositório. Não implemente funcionalidades grandes sem atualizar a documentação e os testes.
