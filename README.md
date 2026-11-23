# GOTCHA

Plataforma para **importar simulados de certificação em vários formatos** (incluindo VCE, condicionado a validação), revisar as questões importadas e treinar com **exames cronometrados**.

> **Status:** planejamento concluído, nenhuma funcionalidade implementada. Acompanhe em [`PLAN.md`](PLAN.md) e na seção [TODO](#todo).

## Princípios

- **Sem IA em nenhuma etapa.** Nenhuma questão, alternativa, gabarito ou explicação é criada por modelo. Uma explicação só aparece se vier do arquivo importado ou se o próprio usuário a escrever.
- **Nada entra no banco sem revisão.** A importação grava apenas rascunhos. Só a confirmação do lote cria questões, e há opção de desfazer.
- **Importação por plugins de formato.** O formato é detectado pelo conteúdo do arquivo, não pela extensão. Vários arquivos podem ser enviados de uma vez, e cada um vira um lote revisável separadamente.
- **Servidor decide tempo e correção.** O gabarito não sai do servidor antes da hora.
- **Sem dumps.** Nenhum conteúdo de exame vem embutido, nada é compartilhado entre contas, e o upload exige atestado de direito de uso.
- **Orientado a testes.** Toda funcionalidade nasce de um teste que falha primeiro. Fixtures são sintéticas.

## Escopo do MVP

Critério de sucesso: **arquivo de simulado → revisão → exame cronometrado.**

| Item | MVP | Release 2 |
| --- | --- | --- |
| Formatos de importação | JSON do app, CSV/XLSX (com mapeamento de colunas), PDF com texto e imagens | HTML, OCR, DOCX, Aiken/GIFT, Moodle XML, QTI |
| VCE | Plugin experimental, **somente se** o spike com arquivos reais der certo | — |
| Tipos de questão pontuados | Múltipla escolha, múltipla resposta, verdadeiro/falso | Arrastar-e-soltar, Sim/Não, hot area, estudo de caso |
| Demais tipos | "Cartão de referência" (visível, não pontua, fora dos exames) ou ignorados | — |

### Sobre o VCE

`.vce` é um formato fechado da Avanset, sem especificação pública nem leitor aberto confiável, e a extensão é compartilhada com formatos não relacionados. O spike termina em um destes resultados:

1. Suporte direto às variantes legíveis.
2. Somente via PDF exportado pelo aplicativo original.
3. Inviável.

Arquivos protegidos são recusados com orientação para exportar pelo aplicativo original. **Não será implementada quebra de senha, de criptografia ou de DRM.**

## Stack planejada

- **Frontend:** React + Vite (SPA)
- **Backend:** FastAPI (Python)
- **Banco:** PostgreSQL como único armazenamento (dados, isolamento por usuário e fila de jobs)
- **Arquitetura:** monólito modular
- **Infra:** Docker Compose, VPS único
- **PDF:** `pdfplumber` e `pypdfium2` (sem PyMuPDF, por ser AGPL)
- **Qualidade:** `uv`, `pytest`, `ruff`, `mypy --strict`

## Notas de domínio

- **Nota escalonada:** exames reais usam nota de 1 a 1000, não linear. O app mostra o percentual real e, no máximo, uma estimativa rotulada como aproximação.
- **Perfis de exame são dados, não código.** Duração e número de questões só entram com fonte oficial conferida. O AZ-800 e o AZ-801 foram aposentados em 30/09/2026 e substituídos pelo AZ-802; confirmar na fonte oficial ao cadastrar os perfis.

## Documentação

- [`PLAN.md`](PLAN.md): fases, decisões, estratégia de testes (TDD), riscos e estimativas.
- [`docs/VALIDACAO.md`](docs/VALIDACAO.md): sistemas similares, taxas de sucesso e classificação das ideias.
- [`CLAUDE.md`](CLAUDE.md): regras de trabalho para o Claude Code neste repositório.

## TODO

Legenda: `[ ]` pendente · `[x]` concluído.

### Preparação

- [x] Planejamento e escopo definidos
- [x] README, PLAN e CLAUDE.md criados
- [ ] Reconstruir o scaffold: `pyproject.toml` (uv), `docker-compose.yml`, `.env.example`, `.editorconfig`
- [ ] Configurar CI: `ruff`, `mypy --strict`, `pytest` e checagem que falha se houver dependência de IA
- [ ] Registrar as decisões arquiteturais (ADRs) em `docs/adr/`
- [x] Validar a ideia contra sistemas similares e classificar as funcionalidades (`docs/VALIDACAO.md`)
- [ ] Configurar `hypothesis`, Playwright e a suíte de contrato de plugins (antes de qualquer importador)
- [ ] Ler os termos da Avanset e registrar o que permitem

### Fase 0 — Spike (bloqueia a Fase 1)

- [ ] Obter 3 a 5 arquivos `.vce` e 3 a 5 PDFs de simulado reais, de origens e versões diferentes (em `samples/`, fora do git)
- [ ] Testar o VCE e decidir entre: suporte direto, só via PDF exportado, ou inviável
- [ ] Testar extração de PDF com `pdfplumber` e `pypdfium2` nos exemplos
- [ ] Medir a taxa de questões extraídas corretamente e fechar o gate de qualidade

### Fase 1 — MVP

- [ ] Modelo de dados: usuários, lotes, rascunhos, questões, exames, tentativas
- [ ] Autenticação e isolamento de dados por usuário
- [ ] Interface do plugin de importação (detecção por conteúdo, upload múltiplo, um lote por arquivo)
- [ ] Importadores: JSON do app, CSV/XLSX com mapeamento de colunas, PDF com texto e imagens
- [ ] Fila de jobs em PostgreSQL e worker sem acesso à rede
- [ ] Tela de revisão: dividir, mesclar, reatribuir alternativas e gabarito
- [ ] Confirmação do lote com opção de desfazer
- [ ] Tipos de questão como plugins: múltipla escolha, múltipla resposta, verdadeiro/falso
- [ ] Cartão de referência para tipos não pontuados
- [ ] Exame cronometrado com tempo e correção decididos no servidor
- [ ] Resultado com percentual real e estimativa escalonada rotulada como aproximação
- [ ] Perfis de exame como dados, com fonte oficial conferida
- [ ] Atestado de direito de uso no upload

### Fase 2 — Release 2

- [ ] Plugin VCE direto (se aprovado no spike)
- [ ] HTML, OCR, DOCX, Aiken/GIFT, Moodle XML e QTI
- [ ] Tipos avançados: arrastar-e-soltar, Sim/Não, hot area, estudo de caso

### Perguntas em aberto

- [ ] Os `.vce` têm senha ou foram comprados/licenciados?
- [ ] Quais outros formatos existem (ProfExam, Boson, Excel, Word, Moodle)?
- [ ] Os simulados têm muitas questões de arrastar-e-soltar, Sim/Não, hot area ou estudo de caso?
- [ ] Uso pessoal ou multiusuário? (assumido: multiusuário, dados isolados)
- [ ] Onde hospedar? (assumido: VPS único com Docker Compose)

## Licença

A definir.
