# CLAUDE.md — regras para este repositório

Projeto: GOTCHA, importador de simulados de certificação com exames cronometrados. Leia `README.md` e `PLAN.md` antes de agir.

## Idioma

- Documentação, mensagens de commit e conversa em português (Brasil).
- Código, identificadores e nomes de arquivos em inglês.

## Regras de produto (não negociáveis)

1. **Nenhuma IA.** Não adicionar bibliotecas, chamadas ou serviços de IA/LLM. Nenhum conteúdo de questão, alternativa, gabarito ou explicação é gerado por modelo.
2. **Nada entra no banco sem revisão.** Importadores gravam apenas rascunhos; só a confirmação do lote cria questões.
3. **Formato detectado pelo conteúdo**, nunca pela extensão.
4. **Servidor decide tempo e correção.** O gabarito não é enviado ao cliente antes da hora.
5. **Sem DRM/criptografia.** Não implementar quebra de senha, criptografia ou proteção de formatos (incluindo VCE). Arquivo protegido é recusado com orientação.
6. **Sem dumps.** Não embutir conteúdo de exame no repositório nem compartilhar bancos entre contas. Arquivos de amostra ficam em `samples/`, ignorada pelo git, e nunca são commitados.
7. **Não usar PyMuPDF** (AGPL). Usar `pdfplumber` e `pypdfium2`.

## Stack

React + Vite (SPA), FastAPI, PostgreSQL (dados, isolamento e fila de jobs), Docker Compose, monólito modular. Gerenciador Python: `uv`.

## Qualidade

Antes de commitar, rodar e passar:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy --strict .
uv run pytest
```

- Código novo exige testes.
- Não pular, desativar ou apagar testes para ficar verde.
- Não afirmar que algo funciona sem tê-lo executado; dizer o que foi e o que não foi verificado.

## Segurança

- Arquivos enviados são não confiáveis: processar em subprocesso com limites de tempo e memória, sem acesso à rede.
- Nunca commitar segredos. Usar `.env` (ignorado) e manter `.env.example` atualizado.
- Dados sempre isolados por usuário.

## Dados de domínio

- Perfis de exame são dados, não código. Duração e número de questões só entram com fonte oficial conferida.
- Nota escalonada: mostrar o percentual real e, no máximo, uma estimativa rotulada como aproximação.

## Git

- Desenvolver na branch `claude/eager-galileo-ilie6p`.
- Commits pequenos e organizados, com mensagem descritiva.
- Não criar Pull Request sem pedido explícito.
- Não reescrever histórico nem fazer push em outras branches sem permissão.

## Ao trabalhar

- Seguir o `PLAN.md`; se uma decisão divergir dele, atualizar o plano e avisar.
- Marcar as tarefas concluídas na seção TODO do `README.md`.
- Em dúvida de escopo, perguntar em vez de assumir.
