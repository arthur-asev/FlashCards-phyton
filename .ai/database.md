# MODELO DE DADOS

## Banco
PostgreSQL + SQLAlchemy + Alembic.

## Entidades
- User
- Subject
- Topic
- Deck
- Card
- Tag
- Review
- ImportJob
- File
- ConversionJob
- AIGeneration

## User
- id
- email
- password_hash
- name
- created_at
- updated_at

## Subject
- id
- name
- description
- created_at
- updated_at

## Topic
- id
- subject_id
- name
- description
- created_at
- updated_at

Subject 1:N Topic. O nome do tópico é único dentro da matéria.

## Deck
- id
- user_id
- subject_id
- name
- description
- created_at
- updated_at

User 1:N Deck.
Subject 1:N Deck.
Deck 1:N Card.

## Card
- id
- deck_id
- topic_id (opcional)
- front
- back
- explanation
- example
- difficulty
- source
- created_at
- updated_at

## Tag
- id
- name

Card N:N Tag usando tabela intermediária.
Card N:1 Topic quando associado a um assunto.

## Review
- id
- card_id
- user_id
- rating
- interval
- ease
- repetitions
- reviewed_at
- next_review_at

## File
- id
- user_id
- filename
- mime_type
- size
- storage_path
- checksum
- created_at

Arquivos físicos não devem ser armazenados diretamente no banco.

## ImportJob
- id
- user_id
- file_id
- status
- total_rows
- processed_rows
- failed_rows
- error_message
- created_at
- started_at
- completed_at

## AIGeneration
- id
- user_id
- deck_id
- provider
- model
- prompt_version
- input_tokens
- output_tokens
- status
- created_at

Nunca armazenar secrets.

## Índices
Considerar:
- user_id
- deck_id
- subject_id
- topic_id
- next_review_at
- created_at
- checksum

Adicionar índices somente com justificativa de acesso/performance.

## Integridade
Utilizar foreign keys, unique constraints, check constraints quando apropriado e transactions.

## Migrations
Toda alteração estrutural via Alembic. Revisar migrations antes de aplicar.

O metadata fica em `app.db.base.Base`; as entidades são importadas por `app.models` para autogenerate. Com o Compose ativo:

```bash
docker compose exec --workdir /app backend alembic upgrade head
docker compose exec --workdir /app backend python -m app.db.seed
```

O seed cria dados de exemplo idempotentes para desenvolvimento. Não é executado automaticamente ao iniciar a API.
