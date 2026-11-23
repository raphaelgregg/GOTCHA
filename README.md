# GOTCHA

Aplicativo **pessoal e local** para **importar exames (simulados) de certificação em vários formatos** (HTML, TXT, PDF, JSON, CSV/XLSX e VCE, este condicionado a validação), revisar as questões importadas, **montar simulados** a partir delas e **treinar com testes cronometrados**.

> **Status:** Entrega 1A implementada e grande parte da 1B (backend, importadores, interface web e testes). O PDF ainda não extrai imagens, e faltam a fila persistente de jobs e os perfis de exame. Veja o [TODO](#todo) e o [`PLAN.md`](PLAN.md).

## Princípios

- **Uso pessoal, local, usuário único.** Roda na sua máquina, escuta só em `127.0.0.1`, sem contas, sem hospedagem, sem telemetria.
- **Sem IA em nenhuma etapa.** Nenhuma questão, alternativa, gabarito ou explicação é criada por modelo. Uma explicação só aparece se vier do arquivo importado ou se o próprio usuário a escrever.
- **Nada entra no banco sem revisão.** A importação grava apenas rascunhos. Só a confirmação do lote cria questões, e há opção de desfazer.
- **Importação por plugins de formato.** O formato é detectado pelo conteúdo do arquivo, não pela extensão. Vários arquivos podem ser selecionados de uma vez, e cada um vira um lote revisável separadamente.
- **Backend decide tempo e correção.** Em modo prova o gabarito não chega à interface antes do fim; o modo estudo mostra a resposta.
- **Sem dumps.** Nenhum conteúdo de exame vem embutido e não há forma de compartilhar bancos.
- **Orientado a testes.** Toda funcionalidade nasce de um teste que falha primeiro. Fixtures são sintéticas.

## Escopo do MVP

Critério de sucesso: **arquivos de simulado → revisão → simulado montado → exame cronometrado.**

"Entender e gerar simulados" significa: o app **entende** os arquivos por análise determinística (sem IA) e **monta** o simulado a partir do banco importado (exames e tópicos, quantidade, sorteio reproduzível, só erradas ou marcadas). Nenhuma questão é criada por modelo.

| Item | Entrega 1A | Entrega 1B | Release 2 |
| --- | --- | --- | --- |
| Formatos | TXT simples, JSON, CSV/XLSX, HTML salvo (questões com alternativas) | ZIP com imagens, PDF com texto e imagens | DOCX, OCR, Aiken/GIFT, Moodle XML, QTI |
| VCE | — | Plugin experimental, **somente se** o spike der certo (hoje: via PDF exportado) | VCE direto, se aprovado |
| Questões corrigidas automaticamente | Múltipla escolha, múltipla resposta ("Select THREE"), verdadeiro/falso | — | — |
| Tipos interativos (hot area, arrastar-e-soltar, simulação, Sim/Não) | — | Importados com imagens e pontuados por **autoavaliação** | Correção automática |
| Estudo de caso | — | Contexto compartilhado entre as questões | — |
| Exame multipágina | Várias páginas no mesmo exame, com deduplicação por (tópico, número) | — | — |
| Gerador de simulado | Sim | — | Estatísticas por tema, revisão espaçada |
| Prova | Modos estudo e prova, marcar, revisar, lista, salvar e retomar | Exhibit com zoom | — |
| Distribuição | `uv run` na máquina | — | Empacotamento desktop |

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

## Como usar

Requisitos: [uv](https://docs.astral.sh/uv/) (Python 3.12+) e Node 20+ (só para compilar a interface).

```bash
uv sync
cd web && npm ci && npm run build && cd ..
uv run gotcha
```

O app abre em `http://127.0.0.1:8765` e guarda os dados em `~/.gotcha` (mude com `--data-dir` ou `GOTCHA_DATA_DIR`).

Fluxo: **importar** arquivos (vários de uma vez) → **revisar** e confirmar → **Novo simulado** → fazer a prova → ver o resultado.

Desenvolvimento:

```bash
uv run pytest                 # testes do backend (use -m "not samples" sem arquivos reais)
uv run ruff check . && uv run mypy
cd web && npm test && npm run dev   # interface com recarga; a API precisa estar em 127.0.0.1:8765
```

Arquivos reais para testar os importadores ficam em `samples/` (ignorada pelo git).

## Estrutura

```text
src/gotcha/
  domain/      modelos, correção por tipo, gerador de simulado, sanitização, exposição
  importers/   um plugin por formato (txt, html, pdf, csv, xlsx, json) + ZIP e detecção
  storage/     SQLite: biblioteca (rascunhos, exames, imagens) e sessões de prova
  api/         FastAPI, segurança local (Host/Origin/cabeçalho) e rotas
  sandbox.py   importação em subprocesso com tempo, memória e sem rede
web/src/       React + Vite: páginas, componentes reutilizáveis, hooks e lógica pura (lib/)
tests/         testes primeiro: unidade, contrato, API, segurança, propriedades, amostras reais
```

## Documentação

- [`PLAN.md`](PLAN.md): plataforma, fases, decisões, estratégia de testes (TDD), riscos e estimativas.
- [`docs/VALIDACAO.md`](docs/VALIDACAO.md): sistemas similares, taxas de sucesso e classificação das ideias.
- [`docs/REQUISITOS-UI.md`](docs/REQUISITOS-UI.md): requisitos de interface com critérios de aceitação.
- [`docs/ARQUITETURA-MULTIMIDIA.md`](docs/ARQUITETURA-MULTIMIDIA.md): questões multimídia, tipos interativos, formato `.gotcha` e plano de testes.
- [`CLAUDE.md`](CLAUDE.md): regras de trabalho para o Claude Code neste repositório.

## TODO

Legenda: `[ ]` pendente · `[x]` concluído.

### Preparação

- [x] Planejamento e escopo definidos
- [x] README, PLAN e CLAUDE.md criados
- [x] Validar a ideia contra sistemas similares e classificar as funcionalidades (`docs/VALIDACAO.md`)
- [x] Definir a plataforma: aplicativo local de usuário único (FastAPI + SPA + SQLite)
- [x] Registrar os requisitos de interface (`docs/REQUISITOS-UI.md`)
- [x] Criar o scaffold: `pyproject.toml` (uv), estrutura de pastas, `.env.example`, `.editorconfig` (`pyproject.toml`, `web/`, CI em `.github/workflows/ci.yml`)
- [x] Configurar CI: `ruff`, `mypy --strict`, `pytest` e checagem que falha se houver dependência de IA ou PyMuPDF
- [x] Configurar `hypothesis`, Playwright e a suíte de contrato de plugins (antes de qualquer importador) (property tests feitos; Playwright e2e ainda não está no repositório)
- [ ] Registrar as decisões arquiteturais (ADRs) em `docs/adr/`
- [ ] Ler os termos da Avanset e registrar o que permitem

### Fase 0 — Spike (bloqueia a Fase 1)

- [x] Receber arquivos `.vce` de exemplo (4 recebidos; ver `docs/SPIKE-VCE.md`)
- [x] Receber e analisar 1 PDF de simulado (AZ-140, 762 páginas, 341 questões): segmentação 100% válida nas 216 com letras (`docs/SPIKE-PDF.md`)
- [ ] Obter mais 2 a 4 PDFs de origens diferentes (inclusive exportados de `.vce` e escaneados), em `samples/`
- [x] Classificar os `.vce` recebidos: resultado provisório **(b) somente via PDF exportado** (`docs/SPIKE-VCE.md`)
- [ ] Confirmar o resultado do VCE exportando um dos `.vce` para PDF no app original
- [x] Analisar uma página HTML salva (50 questões; metade com imagem): viável, mas faltou a pasta de imagens (`docs/SPIKE-HTML.md`)
- [x] Analisar mais 2 páginas HTML e 1 TXT convertido por IA: exame multipágina, 53% das questões sem alternativas (`docs/SPIKE-HTML.md`)
- [x] Decisão do usuário: **todos os formatos e tipos de questão recebidos entram no escopo**, incluindo PDF, e o app deve montar simulados a partir deles
- [x] Comparar `pdfplumber` e `pypdfium2` no PDF recebido (`pypdfium2` ≈ 10× mais rápido; mesma extração, ordem de linhas diferente)
- [ ] Medir a taxa de questões extraídas corretamente e fechar o gate de qualidade
- [ ] Converter as descobertas em casos de teste com fixtures sintéticas

### Fase 1 — Entrega 1A: núcleo utilizável (cada item começa pelo teste)

**Fundação e segurança local**

- [x] Modelo de dados SQLite: lotes, rascunhos, exames, tópicos, questões, sessões, tentativas
- [x] Servidor só em `127.0.0.1`, validação de `Host`/`Origin` e token anti-CSRF (proteção por cabeçalho `X-GOTCHA` + Host/Origin; sem token por sessão)
- [x] Sanitização de HTML dos enunciados importados

**Núcleo de domínio**

- [x] Chave de questão (exame, tópico, número)
- [x] Tipos de questão como plugins: múltipla escolha, múltipla resposta (quantidade exata), verdadeiro/falso
- [x] Corretores e cálculo de nota

**Importação**

- [x] Interface do plugin de importação (detecção por conteúdo, vários arquivos, um lote por arquivo)
- [x] Importador de TXT simples (linhas indentadas, sem presumir acentuação, marcadores de imagem e de configuração manual)
- [x] Importadores de JSON e CSV/XLSX com mapeamento de colunas
- [x] Importador de HTML salvo (questões com alternativas, resposta, votos, tabelas e código no enunciado)
- [ ] Fila de jobs em SQLite (o subprocesso com tempo, memória e sem rede já existe; a fila persistente não)

**Revisão e biblioteca**

- [ ] Tela de revisão: dividir (editar, unir, excluir e reatribuir gabarito já existem)
- [x] Agrupar vários arquivos no mesmo exame, com deduplicação por (tópico, número)
- [x] Confirmação do lote com opção de desfazer
- [x] Lista de exames: adicionar, renomear, remover, propriedades, histórico (histórico em página própria)

**Gerador de simulado**

- [x] Escolher exames e tópicos, quantidade, ordem aleatória reproduzível por semente
- [x] Filtros: só erradas, só marcadas, só não respondidas
- [x] Salvar e reutilizar a definição do simulado

**Prova**

- [x] Modos estudo e prova (gabarito ausente da interface em modo prova)
- [x] Marcar, revisar, mostrar lista, anterior/próxima
- [x] Cronômetro com o backend como fonte do tempo
- [x] Salvar sessão e retomar
- [ ] Estimativa escalonada rotulada como aproximação (o percentual real já aparece)
- [ ] Perfis de exame como dados, com fonte oficial conferida

### Fase 1 — Entrega 1B: imagens, interativos e PDF

- [x] Entrada em ZIP (página + pasta de recursos) e arquivo único; "anexo ausente" quando faltar imagem
- [x] Exhibit com zoom e imagens nos enunciados
- [x] Estudo de caso como entidade com contexto compartilhado
- [x] Tipos interativos importados com imagem da resposta, pontuados por autoavaliação ("revelar e marcar")
- [x] Resultado separando pontuação automática e autoavaliada
- [x] Importador de PDF com texto e imagens (`pdfplumber` e `pypdfium2`) e ferramentas de revisão para layouts irregulares (texto; imagens do PDF ainda não são extraídas)
- [x] Exportar e importar o banco (JSON)
- [ ] Aviso de direito de uso no primeiro uso

### Fase 1C — Multimídia e tipos interativos (requisito adicional)

Desenho entregue em `docs/ARQUITETURA-MULTIMIDIA.md`; implementação aguarda as decisões da seção 16.

- [x] Apresentar o desenho: modelos, recursos, hash, coordenadas, Active Screen, Case Study, Lab, preservação e testes
- [ ] A: modelo canônico v2, registro de tipos, loja de recursos por hash, pacote `.gotcha` e migração
- [ ] B: múltipla escolha e seleção portadas; Build List; Drag and Drop; Hot Area com editor de regiões
- [ ] C: Case Study como entidade com editor de contexto
- [ ] D: editor universal com gestão de mídia, prévia e conversão de tipo
- [ ] E: imagens do PDF com posição, órfãos e relatório de conversão
- [ ] F: Active Screen (motor declarativo e construtor)
- [ ] G: Lab (simulado, instruções externas e real, sempre rotulados)

### Fase 2 — Release 2

- [ ] Plugin VCE direto (se aprovado no spike)
- [ ] OCR, DOCX, Aiken/GIFT, Moodle XML e QTI
- [ ] Correção automática de tipos interativos
- [ ] Estatísticas por tema e revisão espaçada
- [ ] Empacotamento como aplicativo desktop

### Perguntas em aberto

- [ ] Os `.vce` têm senha ou foram comprados/licenciados? Há a edição Pro do app original?
- [ ] Há outros formatos além de HTML, TXT, PDF e VCE (ProfExam, Boson, Excel, Word, Moodle)?
- [x] Tipos de questão: cerca de metade das amostras é interativa (hot area, arrastar-e-soltar, simulação); todos devem ser importados
- [ ] Qual sistema operacional será usado?
- [x] Uso pessoal ou multiusuário? **Pessoal, usuário único, local.**

## Licença

A definir.
