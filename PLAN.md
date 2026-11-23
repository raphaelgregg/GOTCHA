# PLAN — GOTCHA

Plano de implementação refinado. Escopo e decisões vêm do planejamento original (versão 2, sem IA), reconstruído a partir do resumo; ajuste onde divergir do original.

- Validação, taxas de sucesso e classificação das ideias: [`docs/VALIDACAO.md`](docs/VALIDACAO.md).
- Requisitos de interface (referência: telas do VCE Player): [`docs/REQUISITOS-UI.md`](docs/REQUISITOS-UI.md).
- Questões multimídia, tipos interativos e formato `.gotcha` (requisito adicional): [`docs/ARQUITETURA-MULTIMIDIA.md`](docs/ARQUITETURA-MULTIMIDIA.md).

> **Estado:** planejamento. Nenhuma funcionalidade foi implementada. Toda funcionalidade será desenvolvida **orientada a testes** (seção 5).

## 1. Objetivo

Aplicativo de **uso pessoal**: o usuário importa exames (simulados) de vários formatos, **todos os tipos de questão incluídos**, e monta simulados a partir deles para treinar certificações.

**Formatos a importar (todos no escopo):** HTML salvo, TXT simples, JSON do app, CSV/XLSX e PDF, mais o VCE se o spike permitir. Exemplos reais já recebidos estão analisados em `docs/SPIKE-HTML.md` e `docs/SPIKE-VCE.md`.

**"Entender e gerar simulados":** o sistema **entende** os arquivos por análise determinística (sem IA) e **gera o simulado** montando-o a partir do banco importado: escolhe exames e tópicos, quantidade, ordem aleatória reproduzível, só erradas ou marcadas, modo e tempo. Nenhuma questão é criada por modelo.

**Critério de sucesso:** arquivos de simulado → revisão → simulado montado → exame cronometrado.

**Fora de escopo:** geração de conteúdo por IA, quebra de proteção/DRM, conteúdo de exame embutido, contas/multiusuário, hospedagem online, compartilhamento de bancos, simulações de laboratório.

## 2. Plataforma (decisão de uso pessoal)

**Aplicativo local de usuário único**, que roda na máquina do usuário com um comando e abre no navegador (`127.0.0.1`).

| Camada | Escolha | Observação |
| --- | --- | --- |
| Interface | React + Vite (SPA), servida pelo próprio backend | Sem PWA e sem hospedagem |
| Backend | FastAPI (Python) | Python tem as bibliotecas de PDF e planilha |
| Armazenamento | **SQLite** (modo WAL) + pasta de dados local | Substitui PostgreSQL: sem servidor, backup copiando a pasta |
| Jobs de importação | Subprocesso com limites de tempo/memória e sem rede, fila em tabela SQLite | Sem broker externo |
| Distribuição | `uv run` na máquina; Docker Compose opcional, só conveniência de desenvolvimento | Empacotar como app desktop (Tauri ou similar) fica para a Fase 2 |
| Celular | Fora do MVP | Acesso pela rede local pode ser avaliado depois |

**Removido do plano anterior:** autenticação, isolamento por usuário, PostgreSQL, VPS, PWA e atestado de direito de uso por upload (vira um aviso no primeiro uso).

**Cuidados que continuam valendo em app local:**

- Escutar só em `127.0.0.1` e validar `Host`/`Origin` com token anti-CSRF, para que um site aberto no navegador não consiga chamar a API local (ataque de DNS rebinding/CSRF).
- Arquivos importados são não confiáveis mesmo sendo seus: subprocesso com limites e sem rede.
- Nenhum dado sai da máquina; sem telemetria.

## 3. Taxa de sucesso (resumo)

Estimativas de julgamento, ainda não medidas (detalhes em `docs/VALIDACAO.md`):

| Escopo | Estimativa |
| --- | --- |
| Produto sem VCE (HTML/TXT/JSON/CSV/PDF → revisão → simulado → exame) | ≈ 80 a 85% (escopo maior que antes) |
| TXT simples e JSON | 90 a 95% |
| HTML salvo, questões com alternativas | 85 a 90% (frágil a mudanças no site) |
| PDF com texto, utilizável após revisão manual | 80 a 85% |
| Tipos interativos (hot area, arrastar-e-soltar) com autoavaliação | 70 a 80%; **depende de as imagens virem junto** |
| Gerador de simulado a partir do banco | ≈ 95% |
| VCE direto | 10 a 20% |
| VCE via PDF exportado do app original | 45 a 60% |
| "Meus `.vce` viram exames" por qualquer caminho | ≈ 50 a 60% |

O maior risco é a premissa de partida (VCE). O spike da Fase 0 substitui estimativa por medição. Para uso pessoal, o risco legal de hospedagem desaparece, mas as regras de não quebrar proteção e não embutir conteúdo continuam.

## 4. Decisões arquiteturais

| # | Decisão | Motivo |
| --- | --- | --- |
| 1 | **Aplicativo local de usuário único** (FastAPI + SPA em `127.0.0.1`) | Uso pessoal; menos peças |
| 2 | React + Vite e FastAPI | Stack conhecida |
| 3 | **SQLite** como único armazenamento | Sem servidor; backup simples; testes de integração mais rápidos |
| 4 | Importadores como plugins que detectam o formato pelo conteúdo | A extensão `.vce` é ambígua |
| 5 | **PDF como formato universal de entrada**; VCE tratado como plugin condicional | Não há parser aberto de VCE; conversores existentes passam pelo PDF |
| 6 | Importação grava só rascunhos; confirmar o lote cria questões, com desfazer | Nada entra sem revisão |
| 7 | Tipos de questão como plugins (componente, corretor, validação) | Adicionar tipos na Fase 2 sem reescrever |
| 8 | Backend decide tempo e correção; em modo prova o gabarito não vai à interface antes do fim | Integridade do treino; modo estudo mostra a resposta |
| 9 | `pdfplumber` + `pypdfium2`, sem PyMuPDF | PyMuPDF é AGPL |
| 10 | Worker de importação em subprocesso com limites e sem rede | Arquivos não confiáveis |
| 11 | Nenhuma biblioteca de IA; CI falha se aparecer uma | Garante o princípio "sem IA" |
| 12 | Perfis de exame são dados, não código | Exames mudam (AZ-800/801 → AZ-802) |
| 13 | Conteúdo rico nas questões: HTML sanitizado, tabelas, código e imagens (exhibits) | Telas de referência mostram tabelas e SQL no enunciado |
| 14 | Desenvolvimento orientado a testes, com fixtures sintéticas | Seção 5 |
| 15 | Interface inspirada no fluxo do VCE Player, **sem copiar marca, logotipo ou arte da Avanset** | Evitar problema de marca |
| 16 | **Todos os formatos recebidos entram no escopo**: HTML salvo, TXT simples, JSON, CSV/XLSX, PDF | Pedido do usuário; amostras reais analisadas |
| 17 | Chave de questão = **(exame, tópico, número)**; vários arquivos podem alimentar o mesmo exame, com deduplicação | Numeração reinicia por tópico e o exame se espalha por páginas |
| 18 | **Estudo de caso** como entidade própria, com contexto compartilhado | Evita repetir o texto em cada questão |
| 19 | **Tipos interativos importados** com enunciado, exhibits e imagem da resposta, pontuados por **autoavaliação** ("revelar e marcar") | Cerca de metade das questões das amostras é desse tipo; sem motor de correção |
| 20 | Resultado separa **pontuação automática** e **autoavaliada** | Não misturar nota objetiva com nota declarada |
| 21 | Entrada aceita **ZIP** (página + pasta de recursos) e arquivo único; imagem ausente marca "anexo ausente" | As imagens das páginas salvas ficam em pasta à parte |
| 22 | **Gerador de simulado** a partir do banco, com sorteio reproduzível por semente | Testável e repetível |
| 23 | **Modelo canônico v2** com tipos próprios: múltipla escolha, múltipla seleção, drag and drop, build list, hot area, active screen, case study (contêiner) e lab; cada tipo com modelo, validador, renderizador, editor, corretor e serializador | Requisito adicional; sem "múltipla escolha disfarçada" |
| 24 | **Pacote `.gotcha`**: ZIP aberto com `manifest`, JSON por questão e mídia embutida, verificado por SHA-256, sem URLs externas | Autossuficiente e portátil |
| 25 | **Recursos por hash SHA-256**, sem recompressão; derivados rotulados (SVG sanitizado, páginas de PDF) | Dedupe e preservação |
| 26 | **Hot Area com coordenadas normalizadas** (retângulo, círculo, polígono) sobre SVG com `viewBox` proporcional | Independe da resolução |
| 27 | **Active Screen declarativo**: componentes de lista fechada, estado, ações e condições em JSON, sem executar código importado; correção no servidor reexecutando o registro de ações | Segurança e gabarito oculto |
| 28 | **Lab** com modo obrigatório (`simulated`, `external_instructions`, `real`) e aviso fixo de que simulação não é execução real | Honestidade com o usuário |
| 29 | **Tipo de transição `self_assessed`** para o que a importação não consegue reconstruir; conversível no editor | As amostras só trazem imagens, sem regiões nem itens (aprovado) |
| 30 | **Editor universal** único para importados e salvos, com gestão de mídia e prévia | Requisito adicional |

Todas ficam como **Proposta** até aprovação do usuário.

## 5. Estratégia de testes (TDD)

Regra: **nenhuma funcionalidade é escrita antes do teste que a descreve.** Ciclo vermelho → verde → refatorar, um comportamento por vez.

### 5.1 Ciclo por funcionalidade

1. Escrever os critérios de aceitação como casos de teste (nomeados pelo comportamento).
2. Rodar e **ver falhar** pelo motivo certo.
3. Implementar o mínimo para passar.
4. Refatorar com os testes verdes.
5. Só então marcar a tarefa no TODO.

### 5.2 Pirâmide de testes

| Nível | O que cobre | Ferramenta |
| --- | --- | --- |
| Unidade | Corretores de questão, cálculo de nota, detecção de formato, normalização de texto | `pytest` |
| Propriedades | Invariantes: dividir→mesclar devolve o original; correção é determinística; nenhum parser levanta exceção não tratada com bytes aleatórios | `hypothesis` |
| Contrato de plugin | Toda implementação de importador/tipo de questão passa a **mesma suíte de contrato** | `pytest` parametrizado |
| Golden files | Cada importador converte arquivos sintéticos para uma saída esperada versionada | `pytest` + `tests/fixtures/` |
| Integração | API + SQLite: lote, revisão, confirmar, desfazer, exame completo, retomar sessão | `pytest` |
| Segurança | Escuta só em localhost, rejeição de `Host`/`Origin` indevido, gabarito ausente em modo prova, limites do subprocesso, arquivo malicioso/zip bomb | `pytest` |
| Ponta a ponta | Fluxo do critério de sucesso: importar → revisar → exame | Playwright |
| Guarda de dependências | Falha se houver biblioteca de IA ou PyMuPDF | teste sobre o lockfile |

### 5.3 Regras de fixtures

- **Somente dados sintéticos** no repositório: arquivos de simulado gerados pelos testes ou escritos à mão. Nunca amostras reais nem conteúdo de exame.
- Arquivos reais do usuário ficam em `samples/` (ignorada pelo git) e alimentam o spike e uma suíte local opcional, marcada e fora do CI.
- Cada bug de importação vira um novo caso de teste antes da correção.

### 5.4 Critérios de qualidade

- Métricas do spike viram **testes de regressão** (taxa mínima de questões extraídas corretamente em fixtures sintéticas representativas).
- Gate no CI: `ruff`, `mypy --strict`, `pytest`; cobertura mínima nas áreas de correção de nota e segurança local (meta inicial: 90% de linhas nesses módulos).
- Teste que falha **não** é desativado para passar.

### 5.5 Como o spike respeita o TDD

O spike é exploratório: seu código é **descartável** e não entra no produto. Dele saem (a) decisões e (b) casos de teste com fixtures sintéticas que reproduzem os problemas encontrados.

## 6. Fases

### Fase 0 — Spike (3 a 5 dias, bloqueia a Fase 1)

1. Ler os termos da Avanset e registrar o que permitem.
2. Obter 3 a 5 `.vce` e 3 a 5 PDFs de simulado reais em `samples/`.
3. VCE: classificar cada arquivo e escolher: (a) suporte direto; (b) somente via PDF exportado pelo app original; (c) inviável.
4. PDF: comparar `pdfplumber` e `pypdfium2`; medir a taxa de questões extraídas corretamente.
5. Converter as descobertas em casos de teste com fixtures sintéticas.
6. Gate: só avançar com o resultado do VCE e a qualidade do PDF definidos.

Arquivo protegido é recusado com orientação de exportar pelo app original. Não implementar quebra de senha, criptografia ou DRM.

### Fase 1 — MVP (camada A), em duas entregas

Tipos corrigidos automaticamente: múltipla escolha, múltipla resposta (quantidade exata, "Select THREE"), verdadeiro/falso. Tipos interativos (hot area, arrastar-e-soltar, simulação, Sim/Não) são importados e pontuados por **autoavaliação**.

Cada bloco começa pelos testes.

**Entrega 1A — núcleo utilizável (sem imagens)**

1. **Fundação:** scaffold local, CI com os gates, modelo de dados SQLite, segurança local (localhost, Host/Origin, CSRF).
2. **Núcleo de domínio:** tipos de questão, corretores, cálculo de nota, chave (exame, tópico, número).
3. **Importação:** interface de plugin e suíte de contrato, vários arquivos, lote por arquivo, fila de jobs, worker sem rede. Importadores: **TXT simples, JSON, CSV/XLSX, HTML salvo (questões com alternativas)**.
4. **Revisão:** rascunhos, dividir, mesclar, reatribuir alternativas e gabarito, confirmar lote, desfazer, **agrupar vários arquivos no mesmo exame com deduplicação**.
5. **Biblioteca:** lista de exames (adicionar, renomear, remover, propriedades, histórico).
6. **Gerador de simulado:** escolher exames e tópicos, quantidade, ordem aleatória por semente, só erradas ou marcadas, salvar a definição.
7. **Exame:** modos estudo e prova, marcar, revisar, lista, salvar e retomar, cronômetro, resultado com percentual real e estimativa rotulada.

**Entrega 1B — imagens, interativos e PDF**

8. **Anexos:** entrada em ZIP e arquivo único, imagens associadas às questões, "anexo ausente", exhibit com zoom.
9. **Estudo de caso:** entidade com contexto compartilhado.
10. **Tipos interativos:** importar enunciado, exhibits e imagem da resposta; modo "revelar e autoavaliar"; resultado separando automática e autoavaliada.
11. **PDF:** extração de texto e imagens com `pdfplumber` e `pypdfium2`, ferramentas de revisão para layouts irregulares.
12. **Dados:** exportar e importar o banco (JSON), aviso de direito de uso no primeiro uso.

### Fase 1C — Multimídia e tipos interativos (requisito adicional, aprovada e implementada)

Desenho, testes e **estado da implementação** em [`docs/ARQUITETURA-MULTIMIDIA.md`](docs/ARQUITETURA-MULTIMIDIA.md) (seção 18). Itens pendentes: galeria de mídia, alvos do Drag and Drop sobre imagem, captura de gráficos vetoriais do PDF e adaptador QTI. Ordem seguida:

1. **A**: modelo canônico v2, registro de tipos, loja de recursos com hash, pacote `.gotcha` e migração.
2. **B**: portar múltipla escolha e seleção; Build List; Drag and Drop; Hot Area com editor de regiões.
3. **C**: Case Study como entidade com editor de contexto.
4. **D**: editor universal (blocos, galeria de mídia, prévia, conversão de tipo).
5. **E**: importadores com imagens do PDF, órfãos e relatório de conversão.
6. **F**: Active Screen.
7. **G**: Lab (reaproveita o motor de F).

### Fase 2 — Release 2 (camada B, mais C se aprovada)

- Aiken, GIFT, Moodle XML; DOCX, QTI, OCR.
- Correção automática de tipos interativos (hoje por autoavaliação); estatísticas por tema; revisão espaçada.
- Empacotamento como aplicativo desktop (Tauri ou similar).
- VCE direto, se o spike aprovar.

## 7. Estimativas

| Escopo | Esforço (dias úteis, 1 pessoa) |
| --- | --- |
| Entrega 1A (núcleo, TXT/JSON/CSV/HTML sem imagens, gerador, exame) | 38 a 60 |
| Entrega 1B (anexos, estudo de caso, interativos, PDF) | 27 a 45 |
| **MVP completo, sem VCE direto** | **65 a 105** (antes 45 a 72; o escopo cresceu: HTML, TXT, multipágina, interativos, gerador) |
| VCE direto (adicional, se aprovado) | 8 a 25 |
| **Fase 1C: multimídia e tipos interativos** (requisito adicional) | **87 a 142** (julgamento; ver o documento de arquitetura) |

São estimativas de julgamento, não medições, e assumem testes. O que mais move a faixa é o PDF e a qualidade das imagens. Entregar em duas etapas permite usar o app já depois da 1A.

## 8. Riscos

| Risco | Impacto | Mitigação |
| --- | --- | --- |
| VCE fechado/protegido | Formato principal pode ficar inviável | Spike; plano B via PDF exportado |
| Usuário sem a edição Pro do app original | Plano B bloqueado | Confirmar antes |
| PDFs irregulares sem IA | Muitas questões mal extraídas | Revisão manual forte; testes de regressão |
| Tipos interativos são cerca de metade das questões | Sem eles o exame fica pela metade | Importar com autoavaliação já no MVP (Entrega 1B) |
| Imagens ausentes nas páginas salvas | Interativos e exhibits inutilizáveis | Aceitar ZIP/arquivo único; marcar "anexo ausente"; avisar no import |
| Dependência das classes CSS do site no importador de HTML | Quebra se o site mudar | Detecção por estrutura; cada mudança vira caso de teste |
| Texto convertido por IA fora do app pode ter erros | Questões ou gabaritos errados | Preferir a fonte original; aviso na revisão; comparar com o HTML quando houver |
| Escopo do MVP maior | Atraso | Duas entregas; 1A já utilizável |
| Hot Area e Drag and Drop importados só têm imagem, sem regiões | Importação automática não reconstrói o tipo | Tipo `self_assessed` de transição e autoria no editor; sem IA |
| Construtor visual de Active Screen com escopo elástico | Atraso e fidelidade baixa | Lista fechada de componentes, fidelidade declarada ao usuário, modelos prontos |
| Laboratório simulado confundido com execução real | Engano do usuário | Modo obrigatório e aviso fixo; GOTCHA nunca acessa infraestrutura de terceiros |
| Engenharia reversa de formato fechado | Conflito com licença | Sem DRM; decisão do usuário (não é aconselhamento jurídico) |
| Servidor local acessível por sites do navegador | Leitura/alteração dos dados | Só localhost, validação Host/Origin, token CSRF, testes |
| Nota escalonada não linear | Estimativa enganosa | Percentual real + estimativa rotulada |
| Perfis de exame desatualizados | Dados errados | Só com fonte oficial |
| Arquivos importados maliciosos | Segurança | Subprocesso com limites, sem rede |
| Fixtures sintéticas não representarem os PDFs reais | Testes verdes, produto ruim | Suíte local com `samples/`; cada falha real vira fixture |
| Copiar a aparência do VCE Player | Problema de marca | Interface própria; sem logotipo, nome ou arte da Avanset |

## 9. Perguntas em aberto

1. Os `.vce` têm senha ou foram comprados/licenciados? Há a edição Pro do app original?
2. Há outros formatos além de HTML, TXT, PDF e VCE (ProfExam, Boson, Excel, Word, Moodle)?
3. ~~Que tipos de questão dominam os simulados?~~ **Resolvido pelas amostras:** cerca de metade é de tipos interativos; todos devem ser importados.
4. Aceitar "VCE → PDF no app original → GOTCHA" como caminho principal?
5. Qual sistema operacional será usado (afeta o empacotamento da Fase 2)?
6. Confirmação final: nenhuma IA em nenhuma etapa.
7. Requisito multimídia: aprovar `self_assessed`, a definição de Hot Area, o formato `.gotcha` em ZIP aberto e a ordem das fases; informar o que é o formato INDEX (ver as decisões em `docs/ARQUITETURA-MULTIMIDIA.md`, seção 16).

**Resolvido:** uso pessoal, usuário único, execução local.

## 10. Fontes a conferir

- Termos da Avanset: https://www.avanset.com/terms-and-conditions.html (não lidos).
- Aposentadoria do AZ-800/AZ-801: https://learn.microsoft.com/credentials/retired-certification-exams.
- ProfExam, Boson ExSim e Anki: capacidades de importação/exportação não verificadas.
