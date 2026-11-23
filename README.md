# GOTCHA

Aplicativo **pessoal e local** para **importar exames (simulados) de certificação em vários formatos** (HTML, TXT, PDF, JSON, CSV/XLSX e VCE, este condicionado a validação), revisar as questões importadas, **montar simulados** a partir delas e **treinar com testes cronometrados**.

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

- [ ] Modelo de dados SQLite: lotes, rascunhos, exames, tópicos, questões, sessões, tentativas
- [ ] Servidor só em `127.0.0.1`, validação de `Host`/`Origin` e token anti-CSRF
- [ ] Sanitização de HTML dos enunciados importados

**Núcleo de domínio**

- [ ] Chave de questão (exame, tópico, número)
- [ ] Tipos de questão como plugins: múltipla escolha, múltipla resposta (quantidade exata), verdadeiro/falso
- [ ] Corretores e cálculo de nota

**Importação**

- [ ] Interface do plugin de importação (detecção por conteúdo, vários arquivos, um lote por arquivo)
- [ ] Importador de TXT simples (linhas indentadas, sem presumir acentuação, marcadores de imagem e de configuração manual)
- [ ] Importadores de JSON e CSV/XLSX com mapeamento de colunas
- [ ] Importador de HTML salvo (questões com alternativas, resposta, votos, tabelas e código no enunciado)
- [ ] Fila de jobs em SQLite e worker em subprocesso, sem rede e com limites

**Revisão e biblioteca**

- [ ] Tela de revisão: dividir, mesclar, reatribuir alternativas e gabarito
- [ ] Agrupar vários arquivos no mesmo exame, com deduplicação por (tópico, número)
- [ ] Confirmação do lote com opção de desfazer
- [ ] Lista de exames: adicionar, renomear, remover, propriedades, histórico

**Gerador de simulado**

- [ ] Escolher exames e tópicos, quantidade, ordem aleatória reproduzível por semente
- [ ] Filtros: só erradas, só marcadas, só não respondidas
- [ ] Salvar e reutilizar a definição do simulado

**Prova**

- [ ] Modos estudo e prova (gabarito ausente da interface em modo prova)
- [ ] Marcar, revisar, mostrar lista, anterior/próxima
- [ ] Cronômetro com o backend como fonte do tempo
- [ ] Salvar sessão e retomar
- [ ] Resultado com percentual real e estimativa escalonada rotulada como aproximação
- [ ] Perfis de exame como dados, com fonte oficial conferida

### Fase 1 — Entrega 1B: imagens, interativos e PDF

- [ ] Entrada em ZIP (página + pasta de recursos) e arquivo único; "anexo ausente" quando faltar imagem
- [ ] Exhibit com zoom e imagens nos enunciados
- [ ] Estudo de caso como entidade com contexto compartilhado
- [ ] Tipos interativos importados com imagem da resposta, pontuados por autoavaliação ("revelar e marcar")
- [ ] Resultado separando pontuação automática e autoavaliada
- [ ] Importador de PDF com texto e imagens (`pdfplumber` e `pypdfium2`) e ferramentas de revisão para layouts irregulares
- [ ] Exportar e importar o banco (JSON)
- [ ] Aviso de direito de uso no primeiro uso

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
