# ARQUITETURA DO SISTEMA

## 1. Visão

```text
Browser
  |
  v
Vue 3 + TypeScript
  |
 HTTP
  |
  v
FastAPI
  |
  +--> Services --> Repositories --> PostgreSQL
  |
  +--> Redis --> Workers
  |
  +--> File Storage
  |
  +--> AI Providers
```

## 2. Backend
Python + FastAPI + Pydantic + SQLAlchemy + Alembic + PostgreSQL + Redis + Pytest.

## 3. Camadas
API → Service → Repository → Database.

Controllers não devem conter regras de negócio complexas.

## 4. Serviços
- FileService
- ImportService
- ConversionService
- DeckService
- CardService
- AIService
- ExportService
- ReviewService

## 5. Importadores
Interface:
```python
class Importer:
    def read(self, file):
        ...
```

Implementações:
- XlsxImporter
- CsvImporter
- XlsImporter
- OdsImporter

## 6. Exportadores
Interface:
```python
class Exporter:
    def export(self, data):
        ...
```

Implementações:
- CsvExporter
- JsonExporter
- XlsxExporter
- AnkiExporter

## 7. IA
```text
AIService
  |
  +-- AIProvider
       +-- OpenAIProvider
       +-- AnthropicProvider
       +-- LocalProvider
       +-- MockProvider
```

## 8. Jobs
Estados:
- PENDING
- PROCESSING
- COMPLETED
- FAILED
- CANCELLED

## 9. Frontend
```text
src/
├── components/
├── views/
├── layouts/
├── stores/
├── services/
├── composables/
├── types/
└── router/
```

## 10. Erros
Resposta consistente:
```json
{
  "error": {
    "code": "INVALID_FILE",
    "message": "Arquivo inválido",
    "details": []
  }
}
```

Não expor stack trace.

## 11. Observabilidade
Implementar logs estruturados, request ID e health checks:
- GET /health
- GET /ready

## 12. Escalabilidade
Manter Modular Monolith no MVP. Permitir separar posteriormente API, workers, Redis, banco, storage e IA.
