# API — CONTRATOS

## Princípios
- REST;
- JSON por padrão;
- `/api/v1/`;
- respostas consistentes;
- validação com Pydantic;
- erros sem stack trace.

## Health
```text
GET /health
GET /ready
```

`/health` confirma que o processo da API está ativo. `/ready` verifica PostgreSQL e Redis; retorna `200` quando ambos respondem e `503` quando alguma dependência está indisponível.

## Arquivos
```text
POST /api/v1/files/upload
GET  /api/v1/files/{id}
GET  /api/v1/files/{id}/preview?sheet_name=&limit=
POST /api/v1/files/{id}/validate
```

O upload valida tamanho, extensão e conteúdo, grava o arquivo em storage e registra nome, MIME detectado, tamanho e SHA-256 no banco. O preview lê CSV, XLSX e XLS, lista abas, aceita seleção por `sheet_name` e limita a resposta a 100 linhas (`limit`, padrão 20). O endpoint de validação recebe `{ "sheet_name": "Sheet1", "mapping": { "front": "Question", "back": "Answer" } }` e normaliza os campos mapeados sem persistir cards. Leituras síncronas são limitadas a 10.000 linhas; ODS ainda não é aceito.

## Imports
```text
POST /api/v1/imports
GET  /api/v1/imports
GET  /api/v1/imports/{id}
POST /api/v1/imports/{id}/validate
POST /api/v1/imports/{id}/process
```

## Decks
```text
GET    /api/v1/decks
POST   /api/v1/decks
GET    /api/v1/decks/{id}
PUT    /api/v1/decks/{id}
DELETE /api/v1/decks/{id}
```

Listagem de decks aceita `page`, `page_size` (máximo 100), `search` e `subject_id`.

## Cards
```text
GET    /api/v1/cards
POST   /api/v1/cards
GET    /api/v1/cards/{id}
PUT    /api/v1/cards/{id}
DELETE /api/v1/cards/{id}
```

Listagem de cards aceita `page`, `page_size` (máximo 100), `search`, `deck_id`, `subject_id`, `topic_id`, `tag`, `difficulty`, `sort_by` e `order`. Cards aceitam tags por nome e um `topic_id` opcional; o tópico precisa pertencer à matéria do deck quando ela estiver definida.

## Matérias, assuntos e tags
```text
GET/POST/PUT/DELETE /api/v1/subjects
GET/POST/PUT/DELETE /api/v1/topics
GET/POST/PUT/DELETE /api/v1/tags
```

Listagens aceitam paginação; matérias, assuntos e tags também aceitam `search`. Não é possível excluir matéria ou assunto ainda referenciado por decks/cards.

## IA
```text
POST /api/v1/ai/generate-cards
GET  /api/v1/ai/generations
GET  /api/v1/ai/generations/{id}
```

O POST recebe `subject`, `topic`, `content`, `quantity` (1–20), `difficulty`, `objective`, `language` e `deck_id` opcional. A saída é validada quanto ao schema, quantidade e duplicatas. O histórico registra status `PROCESSING`, `COMPLETED` ou `FAILED` e os cards gerados como draft; nenhum card é criado automaticamente. Use o CRUD de cards após revisão.

`AI_PROVIDER` aceita `mock` (padrão) ou `openai`. OpenAI usa `AI_API_KEY`, `AI_MODEL`, `AI_BASE_URL` e `AI_TIMEOUT_SECONDS` no ambiente; a chave não é retornada nem armazenada no histórico. Falhas do provider e respostas inválidas são registradas com códigos sanitizados.

## Exportação
```text
POST /api/v1/export/csv
POST /api/v1/export/json
POST /api/v1/export/xlsx
```

Os três endpoints recebem `{ "cards": [{ "front": "...", "back": "...", "tags": [] }] }` e retornam um anexo com nome `flashcards.<formato>`. Cada solicitação aceita até 10.000 cards; os campos extras incluem explanation, example, difficulty, subject, topic e source. Tags são listas no JSON e texto separado por `; ` em CSV/XLSX.

## Reviews
```text
POST /api/v1/cards/{id}/review
GET  /api/v1/reviews/due
```

## Erros
Formato:
```json
{
  "error": {
    "code": "INVALID_FILE",
    "message": "Arquivo inválido",
    "details": []
  }
}
```

Códigos sugeridos:
- VALIDATION_ERROR
- INVALID_FILE
- FILE_TOO_LARGE
- IMPORT_FAILED
- CARD_NOT_FOUND
- DECK_NOT_FOUND
- AI_PROVIDER_ERROR
- EXPORT_FAILED
- INTERNAL_ERROR

## Paginação
Listagens devem aceitar parâmetros como:
- page
- page_size
- search
- sort
- order

Não retornar grandes coleções sem paginação.

## Idempotência
Operações que possam gerar jobs duplicados devem considerar idempotency keys ou checksum quando apropriado.

## Compatibilidade
Mudanças incompatíveis devem gerar nova versão da API.
