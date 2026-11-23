# CLAUDE.md — regras para este repositório

Projeto: GOTCHA, importador de simulados de certificação com exames cronometrados. Leia `README.md` e `PLAN.md` antes de agir.

## Idioma

- Documentação, mensagens de commit e conversa em português (Brasil).
- Código, identificadores e nomes de arquivos em inglês.

## Regras de produto (não negociáveis)

1. **Nenhuma IA.** Não adicionar bibliotecas, chamadas ou serviços de IA/LLM. Nenhum conteúdo de questão, alternativa, gabarito ou explicação é gerado por modelo. "Gerar simulado" significa **montar** o exame a partir de questões já importadas (filtros, quantidade, sorteio por semente); o app "entende" os arquivos por análise determinística.
2. **Nada entra no banco sem revisão.** Importadores gravam apenas rascunhos; só a confirmação do lote cria questões.
3. **Formato detectado pelo conteúdo**, nunca pela extensão.
4. **O backend decide tempo e correção.** Em modo prova o gabarito não é enviado à interface antes do fim; o modo estudo mostra a resposta.
5. **Sem DRM/criptografia.** Não implementar quebra de senha, criptografia ou proteção de formatos (incluindo VCE). Arquivo protegido é recusado com orientação.
6. **Sem dumps.** Não embutir conteúdo de exame no repositório nem criar qualquer forma de compartilhar ou publicar bancos. Arquivos de amostra ficam em `samples/`, ignorada pelo git, e nunca são commitados.
7. **Uso pessoal, local e de usuário único.** Sem contas, sem autenticação multiusuário, sem hospedagem online, sem telemetria. O servidor escuta só em `127.0.0.1`.
8. **Interface própria.** Inspirada no fluxo do VCE Player (ver `docs/REQUISITOS-UI.md`), sem copiar logotipo, nome, cores de marca ou arte da Avanset.
9. **Não usar PyMuPDF** (AGPL). Usar `pdfplumber` e `pypdfium2`.

## Stack

React + Vite (SPA servida pelo backend), FastAPI, SQLite (dados e fila de jobs), monólito modular, execução local. Docker Compose é opcional (só conveniência de desenvolvimento). Gerenciador Python: `uv`.

## Desenvolvimento orientado a testes (obrigatório)

- **Teste primeiro.** Nenhuma funcionalidade ou correção de bug é escrita antes do teste que a descreve. Ciclo: vermelho (ver o teste falhar pelo motivo certo) → verde (mínimo para passar) → refatorar.
- Nomear testes pelo comportamento esperado, não pela implementação.
- Plugins (importadores, tipos de questão) devem passar a mesma suíte de contrato.
- Importadores têm testes de golden file com fixtures **sintéticas** em `tests/fixtures/`. Nunca commitar amostras reais nem conteúdo de exame.
- Todo bug de importação vira um caso de teste antes da correção.
- Código de spike é descartável: não entra no produto; o que se aproveita são decisões e casos de teste.
- Detalhes em `PLAN.md`, seção 4.

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
- Escutar só em `127.0.0.1`; validar `Host` e `Origin` e usar token anti-CSRF, para que sites abertos no navegador não acessem a API local.
- Sanitizar todo HTML de enunciados importados antes de renderizar.

## Dados de domínio

- Perfis de exame são dados, não código. Duração e número de questões só entram com fonte oficial conferida.
- Nota escalonada: mostrar o percentual real e, no máximo, uma estimativa rotulada como aproximação.

## Git

- Desenvolver na branch `claude-dev`.
- Commits pequenos e organizados, com mensagem descritiva.
- Não criar Pull Request sem pedido explícito.
- Não reescrever histórico nem fazer push em outras branches sem permissão.

## Ao trabalhar

- Seguir o `PLAN.md`; se uma decisão divergir dele, atualizar o plano e avisar.
- Marcar as tarefas concluídas na seção TODO do `README.md`.
- Em dúvida de escopo, perguntar em vez de assumir.
