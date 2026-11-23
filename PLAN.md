# PLAN — GOTCHA

Plano de implementação refinado. Escopo e decisões vêm do planejamento original (versão 2, sem IA), reconstruído a partir do resumo; ajuste onde divergir do original.

- Validação, taxas de sucesso e classificação das ideias: [`docs/VALIDACAO.md`](docs/VALIDACAO.md).
- Requisitos de interface (referência: telas do VCE Player): [`docs/REQUISITOS-UI.md`](docs/REQUISITOS-UI.md).

> **Estado:** planejamento. Nenhuma funcionalidade foi implementada. Toda funcionalidade será desenvolvida **orientada a testes** (seção 5).

## 1. Objetivo

Aplicativo de **uso pessoal**: o usuário importa exames (simulados) de vários formatos e faz testes para treinar certificações.

**Critério de sucesso:** arquivo de simulado → revisão → exame cronometrado.

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
| Produto sem VCE (JSON/CSV/PDF → revisão → exame) | ≈ 85 a 90% (subiu um pouco: menos infraestrutura) |
| PDF com texto, utilizável após revisão manual | 80 a 85% |
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

### Fase 1 — MVP (camada A)

Formatos: JSON do app, CSV/XLSX, PDF com texto e imagens. Tipos pontuados: múltipla escolha, múltipla resposta (com quantidade exata, "Select THREE"), verdadeiro/falso. Demais tipos viram cartão de referência ou são ignorados.

Blocos, cada um iniciado pelos testes:

1. **Fundação:** scaffold local, CI com os gates, modelo de dados SQLite, segurança local (localhost, Host/Origin, CSRF).
2. **Núcleo de domínio:** tipos de questão, corretores, cálculo de nota (maior valor, menor risco).
3. **Importação:** interface de plugin e suíte de contrato, seleção de vários arquivos, lote por arquivo, fila de jobs, worker sem rede, importadores do MVP.
4. **Revisão:** rascunhos, dividir, mesclar, reatribuir alternativas e gabarito, confirmar lote, desfazer.
5. **Biblioteca:** lista de exames (adicionar, renomear, remover, propriedades, histórico), várias provas por arquivo.
6. **Exame:** perfis como dados, modos estudo e prova, marcar questão, revisar, mostrar lista, exhibit, salvar e retomar sessão, resultado com percentual real e estimativa rotulada.
7. **Dados:** exportar e importar o banco (JSON), aviso de direito de uso no primeiro uso.

### Fase 2 — Release 2 (camada B, mais C se aprovada)

- Aiken, GIFT, Moodle XML; HTML, DOCX, QTI, OCR.
- Tipos avançados; estatísticas por tema; revisão espaçada.
- Empacotamento como aplicativo desktop (Tauri ou similar).
- VCE direto, se o spike aprovar.

## 7. Estimativas

| Escopo | Esforço (dias úteis, 1 pessoa) |
| --- | --- |
| MVP sem VCE direto | **45 a 72** (antes 58 a 87; saíram autenticação, isolamento, hospedagem e PostgreSQL) |
| VCE direto (adicional, se aprovado) | 8 a 25 |

A redução é julgamento, não medição. As faixas assumem testes. O spike as estreita.

## 8. Riscos

| Risco | Impacto | Mitigação |
| --- | --- | --- |
| VCE fechado/protegido | Formato principal pode ficar inviável | Spike; plano B via PDF exportado |
| Usuário sem a edição Pro do app original | Plano B bloqueado | Confirmar antes |
| PDFs irregulares sem IA | Muitas questões mal extraídas | Revisão manual forte; testes de regressão |
| Tipos avançados dominando os simulados | MVP cobre pouco | Cartão de referência; subir tipos avançados |
| Engenharia reversa de formato fechado | Conflito com licença | Sem DRM; decisão do usuário (não é aconselhamento jurídico) |
| Servidor local acessível por sites do navegador | Leitura/alteração dos dados | Só localhost, validação Host/Origin, token CSRF, testes |
| Nota escalonada não linear | Estimativa enganosa | Percentual real + estimativa rotulada |
| Perfis de exame desatualizados | Dados errados | Só com fonte oficial |
| Arquivos importados maliciosos | Segurança | Subprocesso com limites, sem rede |
| Fixtures sintéticas não representarem os PDFs reais | Testes verdes, produto ruim | Suíte local com `samples/`; cada falha real vira fixture |
| Copiar a aparência do VCE Player | Problema de marca | Interface própria; sem logotipo, nome ou arte da Avanset |

## 9. Perguntas em aberto

1. Os `.vce` têm senha ou foram comprados/licenciados? Há a edição Pro do app original?
2. Quais outros formatos existem (ProfExam, Boson, Excel, Word, Moodle)?
3. Que tipos de questão dominam os simulados?
4. Aceitar "VCE → PDF no app original → GOTCHA" como caminho principal?
5. Qual sistema operacional será usado (afeta o empacotamento da Fase 2)?
6. Confirmação final: nenhuma IA em nenhuma etapa.

**Resolvido:** uso pessoal, usuário único, execução local.

## 10. Fontes a conferir

- Termos da Avanset: https://www.avanset.com/terms-and-conditions.html (não lidos).
- Aposentadoria do AZ-800/AZ-801: https://learn.microsoft.com/credentials/retired-certification-exams.
- ProfExam, Boson ExSim e Anki: capacidades de importação/exportação não verificadas.
