# GOTCHA

Aplicativo **pessoal e local** para **importar exames (simulados) de certificação em vários formatos** (incluindo VCE, condicionado a validação), revisar as questões importadas e **treinar com testes cronometrados**.

> **Status:** planejamento concluído, nenhuma funcionalidade implementada. Acompanhe em [`PLAN.md`](PLAN.md) e na seção [TODO](#todo).

## Princípios

- **Uso pessoal, local, usuário único.** Roda na sua máquina, escuta só em `127.0.0.1`, sem contas, sem hospedagem, sem telemetria.
- **Sem IA em nenhuma etapa.** Nenhuma questão, alternativa, gabarito ou explicação é criada por modelo. Uma explicação só aparece se vier do arquivo importado ou se o próprio usuário a escrever.
- **Nada entra no banco sem revisão.** A importação grava apenas rascunhos. Só a confirmação do lote cria questões, e há opção de desfazer.
- **Importação por plugins de formato.** O formato é detectado pelo conteúdo do arquivo, não pela extensão. Vários arquivos podem ser selecionados de uma vez, e cada um vira um lote revisável separadamente.
- **Backend decide tempo e correção.** Em modo prova o gabarito não chega à interface antes do fim; o modo estudo mostra a resposta.
- **Sem dumps.** Nenhum conteúdo de exame vem embutido e não há forma de compartilhar bancos.
- **Orientado a testes.** Toda funcionalidade nasce de um teste que falha primeiro. Fixtures são sintéticas.

## Escopo do MVP

Critério de sucesso: **arquivo de simulado → revisão → exame cronometrado.**

| Item | MVP | Release 2 |
| --- | --- | --- |
| Formatos de importação | JSON do app, CSV/XLSX (com mapeamento de colunas), PDF com texto e imagens | HTML, OCR, DOCX, Aiken/GIFT, Moodle XML, QTI |
| VCE | Plugin experimental, **somente se** o spike com arquivos reais der certo | — |
| Tipos de questão pontuados | Múltipla escolha, múltipla resposta (inclui "Select THREE"), verdadeiro/falso | Arrastar-e-soltar, Sim/Não, hot area, estudo de caso |
| Demais tipos | "Cartão de referência" (visível, não pontua, fora dos exames) ou ignorados | — |
| Prova | Modos estudo e prova, marcar, revisar, lista, exhibit, salvar e retomar sessão | Estatísticas por tema, revisão espaçada |
| Distribuição | `uv run` na máquina | Empacotamento desktop (Tauri ou similar) |

Os requisitos de tela, baseados no VCE Player, estão em [`docs/REQUISITOS-UI.md`](docs/REQUISITOS-UI.md). A interface será própria, sem a marca da Avanset.

### Sobre o VCE

`.vce` é um formato fechado da Avanset, sem especificação pública nem leitor aberto confiável, e a extensão é compartilhada com formatos não relacionados. O spike termina em um destes resultados:

1. Suporte direto às variantes legíveis.
2. Somente via PDF exportado pelo aplicativo original.
3. Inviável.

Arquivos protegidos são recusados com orientação para exportar pelo aplicativo original. **Não será implementada quebra de senha, de criptografia ou de DRM.**

## Stack planejada

- **Interface:** React + Vite (SPA), servida pelo backend
- **Backend:** FastAPI (Python)
- **Armazenamento:** SQLite e uma pasta de dados local (inclui a fila de jobs de importação)
- **Arquitetura:** monólito modular, execução local
- **PDF:** `pdfplumber` e `pypdfium2` (sem PyMuPDF, por ser AGPL)
- **Qualidade:** `uv`, `pytest`, `hypothesis`, `ruff`, `mypy --strict`, Playwright
- **Docker Compose:** opcional, só conveniência de desenvolvimento

## Notas de domínio

- **Nota escalonada:** exames reais usam nota de 1 a 1000, não linear. O app mostra o percentual real e, no máximo, uma estimativa rotulada como aproximação.
- **Perfis de exame são dados, não código.** Duração e número de questões só entram com fonte oficial conferida. O AZ-800 e o AZ-801 foram aposentados em 30/09/2026 e substituídos pelo AZ-802; confirmar na fonte oficial ao cadastrar os perfis.

## Documentação

- [`PLAN.md`](PLAN.md): plataforma, fases, decisões, estratégia de testes (TDD), riscos e estimativas.
- [`docs/VALIDACAO.md`](docs/VALIDACAO.md): sistemas similares, taxas de sucesso e classificação das ideias.
- [`docs/REQUISITOS-UI.md`](docs/REQUISITOS-UI.md): requisitos de interface com critérios de aceitação.
- [`CLAUDE.md`](CLAUDE.md): regras de trabalho para o Claude Code neste repositório.

## TODO

Legenda: `[ ]` pendente · `[x]` concluído.

### Preparação

- [x] Planejamento e escopo definidos
- [x] README, PLAN e CLAUDE.md criados
- [x] Validar a ideia contra sistemas similares e classificar as funcionalidades (`docs/VALIDACAO.md`)
- [x] Definir a plataforma: aplicativo local de usuário único (FastAPI + SPA + SQLite)
- [x] Registrar os requisitos de interface (`docs/REQUISITOS-UI.md`)
- [ ] Criar o scaffold: `pyproject.toml` (uv), estrutura de pastas, `.env.example`, `.editorconfig`
- [ ] Configurar CI: `ruff`, `mypy --strict`, `pytest` e checagem que falha se houver dependência de IA ou PyMuPDF
- [ ] Configurar `hypothesis`, Playwright e a suíte de contrato de plugins (antes de qualquer importador)
- [ ] Registrar as decisões arquiteturais (ADRs) em `docs/adr/`
- [ ] Ler os termos da Avanset e registrar o que permitem

### Fase 0 — Spike (bloqueia a Fase 1)

- [x] Receber arquivos `.vce` de exemplo (4 recebidos; ver `docs/SPIKE-VCE.md`)
- [ ] Obter 3 a 5 PDFs de simulado reais, de origens e versões diferentes (em `samples/`, fora do git)
- [x] Classificar os `.vce` recebidos: resultado provisório **(b) somente via PDF exportado** (`docs/SPIKE-VCE.md`)
- [ ] Confirmar o resultado do VCE exportando um dos `.vce` para PDF no app original
- [ ] Testar extração de PDF com `pdfplumber` e `pypdfium2` nos exemplos
- [ ] Medir a taxa de questões extraídas corretamente e fechar o gate de qualidade
- [ ] Converter as descobertas em casos de teste com fixtures sintéticas

### Fase 1 — MVP (cada item começa pelo teste)

**Fundação e segurança local**

- [ ] Modelo de dados SQLite: lotes, rascunhos, questões, exames, sessões, tentativas
- [ ] Servidor só em `127.0.0.1`, validação de `Host`/`Origin` e token anti-CSRF
- [ ] Sanitização de HTML dos enunciados importados

**Núcleo de domínio**

- [ ] Tipos de questão como plugins: múltipla escolha, múltipla resposta (quantidade exata), verdadeiro/falso
- [ ] Corretores e cálculo de nota
- [ ] Cartão de referência para tipos não pontuados

**Importação**

- [ ] Interface do plugin de importação (detecção por conteúdo, vários arquivos, um lote por arquivo)
- [ ] Importadores: JSON do app, CSV/XLSX com mapeamento de colunas, PDF com texto e imagens
- [ ] Fila de jobs em SQLite e worker em subprocesso, sem rede e com limites
- [ ] Suporte a exhibits (imagens anexas) e tabelas/código nos enunciados

**Revisão**

- [ ] Tela de revisão: dividir, mesclar, reatribuir alternativas e gabarito
- [ ] Confirmação do lote com opção de desfazer

**Biblioteca**

- [ ] Lista de exames: adicionar, renomear, remover, propriedades, histórico
- [ ] Vários exames dentro de um mesmo arquivo ("Exam A", "Exam B")

**Prova**

- [ ] Modos estudo e prova (gabarito ausente da interface em modo prova)
- [ ] Marcar questão, revisar (marcadas/não respondidas), mostrar lista, anterior/próxima
- [ ] Botão Exhibit
- [ ] Cronômetro com o backend como fonte do tempo
- [ ] Salvar sessão e retomar
- [ ] Resultado com percentual real e estimativa escalonada rotulada como aproximação
- [ ] Perfis de exame como dados, com fonte oficial conferida

**Dados**

- [ ] Exportar e importar o banco (JSON)
- [ ] Aviso de direito de uso no primeiro uso

### Fase 2 — Release 2

- [ ] Plugin VCE direto (se aprovado no spike)
- [ ] HTML, OCR, DOCX, Aiken/GIFT, Moodle XML e QTI
- [ ] Tipos avançados: arrastar-e-soltar, Sim/Não, hot area, estudo de caso
- [ ] Estatísticas por tema e revisão espaçada
- [ ] Empacotamento como aplicativo desktop

### Perguntas em aberto

- [ ] Os `.vce` têm senha ou foram comprados/licenciados? Há a edição Pro do app original?
- [ ] Quais outros formatos existem (ProfExam, Boson, Excel, Word, Moodle)?
- [ ] Os simulados têm muitas questões de arrastar-e-soltar, Sim/Não, hot area ou estudo de caso?
- [ ] Qual sistema operacional será usado?
- [x] Uso pessoal ou multiusuário? **Pessoal, usuário único, local.**

## Licença

A definir.
