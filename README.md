# Flashcard Platform

Plataforma local para importar planilhas, criar decks e cards, revisar conhecimento e gerar conteúdo com IA.

## Stack
- Backend: Python + FastAPI
- Frontend: Vue 3 + TypeScript + Vite
- Banco: PostgreSQL
- Fila/cache: Redis
- Worker: processo Python para jobs assíncronos
- Orquestração: Docker Compose

## Requisitos
- Docker Desktop ou Docker Engine com Compose
- Git
- Navegador web (Chrome, Edge, Firefox)

## 1) Preparando o ambiente
No diretório do projeto:

```bash
cp .env.example .env
```

No PowerShell do Windows:

```powershell
Copy-Item .env.example .env
```

O arquivo `.env` já vem com valores prontos para desenvolvimento local:

```env
APP_ENV=development
APP_NAME=Flashcard Platform
DATABASE_URL=postgresql+psycopg://flashcard:flashcard@postgres:5432/flashcard
REDIS_URL=redis://redis:6379/0
SECRET_KEY=change-me-in-development
CORS_ORIGINS=http://localhost:5173
MAX_UPLOAD_SIZE_MB=25
STORAGE_PATH=/storage
AI_PROVIDER=mock
AI_API_KEY=
AI_MODEL=gpt-4o-mini
AI_BASE_URL=https://api.openai.com/v1
AI_TIMEOUT_SECONDS=30
```

> Se quiser testar a geração com OpenAI real, altere `AI_PROVIDER=openai` e coloque sua `AI_API_KEY`.

## 2) Subindo o projeto localmente
Na raiz do repositório:

```bash
docker compose up -d --build
```

Espere alguns segundos e verifique os containers:

```bash
docker compose ps
```

Se quiser acompanhar os logs:

```bash
docker compose logs -f backend frontend worker
```

## 3) Endpoints e URLs de acesso
Quando tudo estiver pronto, você deve conseguir abrir:

- Frontend: http://localhost:5173
- API: http://localhost:8000
- Swagger/OpenAPI: http://localhost:8000/docs
- Health check: http://localhost:8000/health
- Readiness check: http://localhost:8000/ready

Teste rápido no terminal:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

Resposta esperada do health:

```json
{"status": "ok"}
```

## 4) Fluxo manual de teste no navegador
### A. Dashboard
1. Abra http://localhost:5173.
2. Confirme que a tela principal carregou corretamente.
3. Verifique se as dashboards, cards pendentes e indicadores aparecem sem erro.

### B. Importar planilha
1. No menu lateral, clique em "Importar".
2. Faça upload de um arquivo CSV/XLSX/XLS.
3. Use uma planilha simples com colunas como:

```csv
front,back,topic,tags
O que é FastAPI?,É um framework web em Python para APIs.,Python,backend;api
Qual comando inicia o app?,docker compose up -d --build,DevOps,docker;setup
```

4. Na etapa de mapeamento, associe:
   - `front` -> front
   - `back` -> back
   - `topic` -> topic
   - `tags` -> tags
5. Confirme a validação e clique para importar.
6. Verifique se a importação termina com sucesso e o novo conteúdo aparece na biblioteca.

### C. Biblioteca e criação manual de cards
1. Abra "Biblioteca".
2. Crie ou edite um deck.
3. Crie um card com:
   - frente: "Qual a capital do Brasil?"
   - verso: "Brasília"
   - tags: "geografia", "brasil"
4. Salve e confirme que o card aparece listado.

### D. Revisão de flashcards
1. Entre em "Revisão".
2. Faça o fluxo de revisão dos cards pendentes.
3. Responda como "Acertou" ou "Precisa revisar".
4. Confirme que a lista e os indicadores de revisão atualizam.

### E. Geração com IA
1. Acesse "Gerar com IA".
2. Informe um tema ou prompt de estudo, como: "crie flashcards de biologia celular".
3. O projeto usa `AI_PROVIDER=mock` por padrão, então a geração será simulada sem depender de chave externa.
4. Confirme que o conteúdo gerado aparece como rascunho e pode ser revisado antes de salvar.

> Para usar a integração real com OpenAI, configure `AI_PROVIDER=openai` e `AI_API_KEY` no arquivo `.env` antes de subir o stack.

## 5) Testando a API diretamente
### Verificar saúde da aplicação

```bash
curl http://localhost:8000/health
```

### Verificar readiness

```bash
curl http://localhost:8000/ready
```

### Listar decks

```bash
curl http://localhost:8000/api/v1/decks
```

### Criar um deck via API

```bash
curl -X POST "http://localhost:8000/api/v1/decks" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "História",
    "description": "Deck de revisão de história",
    "subject_id": null
  }'
```

### Enviar arquivo para upload

```bash
echo -e "front,back,topic,tags\nCapital do Brasil?,Brasília,Geografia,brasil;capital" > /tmp/flashcards.csv
curl -X POST "http://localhost:8000/api/v1/files/upload" -F "file=@/tmp/flashcards.csv"
```

### Pré-visualizar o arquivo enviado

```bash
curl "http://localhost:8000/api/v1/files/{file_id}/preview?limit=10"
```

Substitua `{file_id}` pelo UUID retornado pelo upload.

## 6) Comandos úteis durante o desenvolvimento
### Rodar testes do backend

```bash
docker compose exec backend pytest
```

### Verificar build do frontend

```bash
docker compose exec frontend npm run build
```

### Reiniciar tudo limpo

```bash
docker compose down -v
```

### Parar os serviços

```bash
docker compose down
```

## 7) Solução de problemas comuns
- Se a aplicação não abrir: confira se os containers estão rodando com `docker compose ps`.
- Se o frontend não carregar: confirme se o backend já respondeu em `http://localhost:8000/ready`.
- Se o upload falhar: verifique o tamanho do arquivo e o formato suportado (CSV/XLS/XLSX).
- Se a IA não gerar dados: confirme o valor de `AI_PROVIDER` e `AI_API_KEY` no `.env`.
- Se houver erro de banco: reinicie os serviços com `docker compose down -v` e suba novamente.

## 8) Checklist de validação rápida
- [ ] Docker subiu sem erros
- [ ] Frontend acessível em http://localhost:5173
- [ ] API pronta em http://localhost:8000/ready
- [ ] Upload de planilha funciona
- [ ] Importação finaliza corretamente
- [ ] Card aparece na biblioteca
- [ ] Revisão funciona
- [ ] Geração de IA responde sem erro

## 9) Dica de uso
Para testar o projeto da forma mais realista, siga este fluxo:

1. Crie um deck
2. Faça upload de uma planilha de exemplo
3. Importe os cards
4. Revise alguns cards na aba de revisão
5. Use a geração com IA para criar novos rascunhos
6. Confirme a experiência completa em um browser local

