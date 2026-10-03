# REGRAS DE DESENVOLVIMENTO

## 1. Geral
Priorizar:
- clareza;
- simplicidade;
- coesão;
- baixo acoplamento;
- testabilidade;
- segurança.

## 2. Python
Seguir PEP 8.

Preferir:
- type hints;
- funções pequenas;
- nomes explícitos;
- dataclasses/Pydantic quando apropriado;
- exceptions específicas.

Evitar:
- funções gigantes;
- variáveis genéricas;
- `except Exception` sem tratamento adequado;
- lógica de negócio dentro de controllers.

## 3. FastAPI
Routes devem ser finas.

Fluxo preferido:
```text
Route → Service → Repository
```

Validação via Pydantic.

## 4. Banco
Não acessar SQL diretamente em todas as partes da aplicação.

Centralizar acesso em repositories/services quando isso melhorar a separação.

Usar migrations.

## 5. Frontend
Usar TypeScript.

Evitar `any` quando houver tipo apropriado.

Separar:
- UI;
- estado;
- comunicação API;
- tipos.

## 6. Segurança
Nunca colocar secrets no código.

Não registrar:
- tokens;
- senhas;
- API keys;
- credenciais.

Validar todos os inputs.

## 7. Arquivos
Nunca confiar apenas na extensão.

Validar:
- MIME;
- tamanho;
- estrutura;
- conteúdo quando necessário.

## 8. IA
Nunca confiar cegamente na saída do modelo.

Sempre:
1. receber;
2. validar;
3. normalizar;
4. verificar;
5. persistir.

## 9. Dependências
Antes de adicionar biblioteca:
1. verificar se já existe solução;
2. avaliar manutenção;
3. avaliar segurança;
4. avaliar licença;
5. justificar.

## 10. Alterações
Antes de editar arquivo existente:
1. ler;
2. entender;
3. localizar dependências;
4. alterar o mínimo necessário.

## 11. Git
Commits devem ser pequenos e descritivos.

Exemplos:
```text
feat: add xlsx importer
fix: validate empty flashcard rows
test: add import service tests
docs: update API contracts
```

## 12. Documentação
Mudanças arquiteturais devem atualizar `.ai/`.

## 13. Não inventar
Não inventar APIs, comandos, bibliotecas ou resultados.

Se não souber:
- declarar incerteza;
- verificar;
- ou marcar como NÃO CONFIRMADO.

## 14. Proibição de destruição
Não executar automaticamente:
- DROP DATABASE;
- DROP TABLE;
- TRUNCATE;
- rm -rf;
- remoção em massa.

Sem confirmação explícita.

## 15. Conclusão de tarefa
Toda tarefa deve terminar com:
- resumo;
- arquivos alterados;
- testes executados;
- resultado;
- riscos conhecidos;
- próxima tarefa sugerida.
