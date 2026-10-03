# REQUISITOS DO SISTEMA

## 1. Visão geral
Plataforma web para processamento de planilhas e criação, organização e revisão de flashcards.

## 2. Objetivos
- reduzir trabalho manual;
- importar grandes quantidades de conteúdo;
- padronizar flashcards;
- organizar por matéria e assunto;
- permitir revisão;
- integrar IA;
- exportar para outras ferramentas.

## 3. Usuário
O MVP será inicialmente para usuário individual. A arquitetura deve permitir posteriormente múltiplos usuários, autenticação, permissões, compartilhamento e sincronização.

## 4. Planilhas
Entradas:
- XLSX
- XLS
- CSV
- ODS, se viável

Saídas:
- CSV
- JSON
- XLSX

Futuro:
- TSV
- TXT
- Anki
- APKG

## 5. Upload
Fluxo:
1. selecionar;
2. upload;
3. visualizar informações;
4. preview;
5. selecionar aba;
6. mapear colunas;
7. validar;
8. confirmar.

## 6. Mapeamento
Permitir:
- front
- back
- explanation
- subject
- topic
- tags
- difficulty
- source

## 7. Validação
Detectar:
- campos obrigatórios ausentes;
- linhas vazias;
- duplicidade;
- conteúdo excessivo;
- conteúdo inválido;
- colunas incompatíveis;
- arquivos inválidos.

## 8. Flashcards
Cada card deve possuir:
- ID;
- frente;
- verso;
- explicação;
- exemplo;
- dificuldade;
- tags;
- matéria;
- assunto;
- origem;
- datas de criação e atualização.

## 9. Decks
Permitir criar, editar, excluir, duplicar, importar, exportar, pesquisar e filtrar.

## 10. IA
Criar camada de abstração para provedores. Não acoplar o sistema a um fornecedor.

## 11. Geração
Entrada:
- matéria;
- assunto;
- conteúdo;
- quantidade;
- dificuldade;
- objetivo;
- idioma.

Validar todo resultado antes de persistir.

## 12. Qualidade
Cards devem ser claros, objetivos, focados em uma ideia, sem duplicação e sem informações inventadas.

## 13. Revisão
Registrar card, usuário, data, resposta, avaliação, intervalo e próxima revisão.

## 14. Processamento assíncrono
Usar background jobs para planilhas grandes, geração de cards, exportação e IA.

## 15. Segurança
Validar uploads, limitar tamanho, proteger credenciais, usar variáveis de ambiente, validar entradas e evitar dados sensíveis nos logs.

## 16. MVP
Considerar funcional quando o usuário puder:
1. subir XLSX;
2. visualizar dados;
3. mapear colunas;
4. validar;
5. importar cards;
6. criar deck;
7. visualizar/editar cards;
8. exportar;
9. executar testes;
10. iniciar ambiente via Docker.
