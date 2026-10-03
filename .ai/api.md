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

## Cards
```text
GET    /api/v1/cards
POST   /api/v1/cards
GET    /api/v1/cards/{id}
PUT    /api/v1/cards/{id}
DELETE /api/v1/cards/{id}
```

## IA
```text
POST /api/v1/ai/generate-cards
GET  /api/v1/ai/generations/{id}
```

## Exportação
```text
POST /api/v1/export/csv
POST /api/v1/export/json
POST /api/v1/export/xlsx
```

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
