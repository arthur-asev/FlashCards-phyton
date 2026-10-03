# ESTRATÉGIA DE TESTES

## Objetivo
Garantir correção, segurança e estabilidade sem depender de serviços externos nos testes unitários.

## Pirâmide
```text
        E2E
       /   \
  Integration
  /         \
Unit / Component
```

## Unitários
Testar:
- parsers;
- validators;
- services;
- repositories isoladamente quando necessário;
- exporters;
- regras de cards;
- repetição espaçada.

## Integração
Testar:
- FastAPI;
- PostgreSQL;
- Redis;
- upload;
- importação;
- exportação;
- jobs.

## E2E
Fluxo principal:
1. abrir aplicação;
2. enviar XLSX;
3. visualizar preview;
4. mapear colunas;
5. validar;
6. importar;
7. criar deck;
8. visualizar cards;
9. editar;
10. exportar.

## IA
Nunca depender de API externa nos testes unitários.

Criar MockProvider/FakeProvider.

Testar:
- schema;
- validação;
- respostas inválidas;
- timeout;
- erro do provedor;
- cards duplicados.

## Fixtures
Criar fixtures para:
- usuário;
- deck;
- cards;
- planilha pequena;
- planilha inválida;
- planilha grande;
- respostas de IA.

## Cobertura
Priorizar cobertura de lógica de negócio e caminhos críticos. Não perseguir cobertura artificial.

## Regra
Toda correção de bug deve, quando possível, adicionar um teste que reproduza o problema.

## Execução
Exemplo:
```bash
pytest
pytest -m unit
pytest -m integration
```

Antes de considerar uma tarefa concluída:
- testes relevantes passam;
- lint passa;
- type checking passa quando configurado;
- nenhuma regressão conhecida foi introduzida.
