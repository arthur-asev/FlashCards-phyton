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
  def export(self, data) -> bytes:
        ...
```

Implementações:
- CsvExporter
- JsonExporter
- XlsxExporter
- AnkiExporter

Os endpoints de exportação recebem uma lista validada de cards e retornam o arquivo como resposta HTTP; tags permanecem como lista em JSON e são unidas por `; ` em CSV/XLSX.

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

`AIProvider` é um Protocol. `AIService` valida schema, quantidade e duplicatas antes de registrar o resultado. OpenAI usa HTTPX; MockProvider é o padrão em desenvolvimento e testes.

## 8. Jobs
Estados:
- PENDING
- PROCESSING
- COMPLETED
- FAILED
- CANCELLED

PostgreSQL é a fonte de verdade do status, tentativas, payload e resultado; Redis transporta IDs na fila. O worker usa claim condicional para tolerar entrega duplicada, retry limitado e recuperação de jobs interrompidos.

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
