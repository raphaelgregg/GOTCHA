# PLAN — GOTCHA

Plano de implementação refinado. Escopo e decisões vêm do planejamento original (versão 2, sem IA), reconstruído a partir do resumo; ajuste onde divergir do original.

Validação, taxas de sucesso e classificação das ideias: [`docs/VALIDACAO.md`](docs/VALIDACAO.md).

> **Estado:** planejamento. Nenhuma funcionalidade foi implementada. Toda funcionalidade será desenvolvida **orientada a testes** (seção 4).

## 1. Objetivo

Permitir que o usuário envie arquivos de simulado em vários formatos, revise as questões importadas e treine com exames cronometrados.

**Critério de sucesso:** arquivo de simulado → revisão → exame cronometrado.

**Fora de escopo:** geração de conteúdo por IA, quebra de proteção/DRM, conteúdo de exame embutido, compartilhamento de bancos entre contas, simulações de laboratório.

## 2. Taxa de sucesso (resumo)

Estimativas de julgamento, ainda não medidas (detalhes em `docs/VALIDACAO.md`):

| Escopo | Estimativa |
| --- | --- |
| Produto sem VCE (JSON/CSV/PDF → revisão → exame) | ≈ 85% |
| PDF com texto, utilizável após revisão manual | 80 a 85% |
| VCE direto | 10 a 20% |
| VCE via PDF exportado do app original | 45 a 60% |
| "Meus `.vce` viram exames" por qualquer caminho | ≈ 50 a 60% |

O maior risco é a premissa de partida (VCE). O spike da Fase 0 substitui estimativa por medição.

## 3. Decisões arquiteturais

| # | Decisão | Motivo |
| --- | --- | --- |
| 1 | Monólito modular com Docker Compose | Simplicidade operacional em um VPS único |
| 2 | React + Vite (SPA) e FastAPI | Stack conhecida, separação clara |
| 3 | PostgreSQL como único armazenamento, inclusive fila de jobs | Evita Redis/broker extra |
| 4 | Importadores como plugins que detectam o formato pelo conteúdo | A extensão `.vce` é ambígua |
| 5 | **PDF como formato universal de entrada**; VCE tratado como plugin condicional | Não há parser aberto de VCE; conversores existentes passam pelo PDF |
| 6 | Importação grava só rascunhos; confirmar o lote cria questões, com desfazer | Nada entra sem revisão humana |
| 7 | Tipos de questão como plugins (componente, corretor, validação) | Adicionar tipos na Fase 2 sem reescrever |
| 8 | Servidor decide tempo e correção; gabarito não sai antes da hora | Integridade do exame |
| 9 | `pdfplumber` + `pypdfium2`, sem PyMuPDF | PyMuPDF é AGPL |
| 10 | Worker de importação em subprocesso com limites e sem rede | Arquivos enviados são não confiáveis |
| 11 | Nenhuma biblioteca de IA; CI falha se aparecer uma | Garante o princípio "sem IA" |
| 12 | Perfis de exame são dados, não código | Exames mudam (AZ-800/801 → AZ-802) |
| 13 | Multiusuário com dados isolados | Premissa assumida; confirmar |
| 14 | Desenvolvimento orientado a testes, com fixtures sintéticas | Seção 4 |

Todas ficam como **Proposta** até aprovação do usuário.

## 4. Estratégia de testes (TDD)

Regra: **nenhuma funcionalidade é escrita antes do teste que a descreve.** Ciclo vermelho → verde → refatorar, um comportamento por vez.

### 4.1 Ciclo por funcionalidade

1. Escrever os critérios de aceitação como casos de teste (nomeados pelo comportamento).
2. Rodar e **ver falhar** pelo motivo certo.
3. Implementar o mínimo para passar.
4. Refatorar com os testes verdes.
5. Só então marcar a tarefa no TODO.

### 4.2 Pirâmide de testes

| Nível | O que cobre | Ferramenta |
| --- | --- | --- |
| Unidade | Corretores de questão, cálculo de nota, detecção de formato, normalização de texto | `pytest` |
| Propriedades | Invariantes: dividir→mesclar devolve o original; correção é determinística; nenhum parser levanta exceção não tratada com bytes aleatórios | `hypothesis` |
| Contrato de plugin | Toda implementação de importador/tipo de questão passa a **mesma suíte de contrato** | `pytest` parametrizado |
| Golden files | Cada importador converte arquivos sintéticos para uma saída esperada versionada | `pytest` + arquivos em `tests/fixtures/` |
| Integração | API + PostgreSQL: lote, revisão, confirmar, desfazer, exame completo | `pytest` + Postgres real (compose) |
| Segurança | Isolamento entre usuários, gabarito ausente da resposta antes da hora, limites do subprocesso, arquivo malicioso/zip bomb | `pytest` |
| Ponta a ponta | Fluxo do critério de sucesso: upload → revisão → exame | Playwright |
| Guarda de dependências | Falha se houver biblioteca de IA ou PyMuPDF | teste sobre o lockfile |

### 4.3 Regras de fixtures

- **Somente dados sintéticos** no repositório: arquivos de simulado gerados pelos próprios testes ou escritos à mão. Nunca amostras reais nem conteúdo de exame.
- Arquivos reais do usuário ficam em `samples/` (ignorada pelo git) e alimentam apenas o spike e uma suíte local opcional, marcada e ignorada no CI.
- Cada bug de importação vira um novo caso de teste antes da correção.

### 4.4 Critérios de qualidade

- Métricas do spike viram **testes de regressão** (por exemplo, taxa mínima de questões extraídas corretamente em fixtures sintéticas representativas).
- Gate no CI: `ruff`, `mypy --strict`, `pytest`; cobertura mínima nas áreas de correção de nota e isolamento de dados (meta inicial: 90% de linhas nesses módulos).
- Um teste que falha **não** é desativado para passar; corrige-se o código ou a especificação.

### 4.5 Como o spike respeita o TDD

O spike é exploratório: seu código é **descartável** e não entra no produto. O que sai dele são (a) decisões e (b) casos de teste com fixtures sintéticas que reproduzem os problemas encontrados. A implementação de produção nasce depois, a partir desses testes.

## 5. Fases

### Fase 0 — Spike (3 a 5 dias, bloqueia a Fase 1)

1. Ler os termos da Avanset e registrar o que permitem.
2. Obter 3 a 5 `.vce` e 3 a 5 PDFs de simulado reais em `samples/`.
3. VCE: classificar cada arquivo e escolher o resultado: (a) suporte direto; (b) somente via PDF exportado pelo app original; (c) inviável.
4. PDF: comparar `pdfplumber` e `pypdfium2`; medir a taxa de questões extraídas corretamente.
5. Converter as descobertas em casos de teste com fixtures sintéticas.
6. Gate: só avançar com o resultado do VCE e a qualidade do PDF definidos.

Arquivo protegido é recusado com orientação de exportar pelo app original. Não implementar quebra de senha, criptografia ou DRM.

### Fase 1 — MVP (camada A)

Formatos: JSON do app, CSV/XLSX, PDF com texto e imagens. Tipos pontuados: múltipla escolha, múltipla resposta, verdadeiro/falso. Demais tipos viram cartão de referência ou são ignorados.

Blocos, cada um iniciado pelos testes:

1. **Fundação:** scaffold, CI com os gates de qualidade, modelo de dados, autenticação, isolamento por usuário.
2. **Núcleo de domínio:** tipos de questão, corretores, cálculo de nota (testes primeiro; é o código de maior valor e menor risco).
3. **Importação:** interface de plugin e suíte de contrato, upload múltiplo, lote por arquivo, fila de jobs, worker sem rede, importadores do MVP.
4. **Revisão:** rascunhos, dividir, mesclar, reatribuir alternativas e gabarito, confirmar lote, desfazer.
5. **Exame:** perfis como dados, modos estudo e prova, cronometragem e correção no servidor, resultado com percentual real e estimativa rotulada.
6. **Conformidade:** atestado de direito de uso, regras de não compartilhamento, exportação do banco.

### Fase 2 — Release 2 (camada B, mais C se aprovada)

- Aiken, GIFT, Moodle XML (formatos abertos); HTML, DOCX, QTI, OCR.
- Tipos avançados; estatísticas por tema; revisão espaçada.
- VCE direto, se o spike aprovar.

## 6. Estimativas

| Escopo | Esforço (dias úteis, 1 pessoa) |
| --- | --- |
| MVP sem VCE direto | 58 a 87 |
| VCE direto (adicional, se aprovado) | 8 a 25 |

TDD tende a aumentar o esforço inicial por funcionalidade e reduzir retrabalho; as faixas acima já assumem testes. O spike estreita as faixas.

## 7. Riscos

| Risco | Impacto | Mitigação |
| --- | --- | --- |
| VCE fechado/protegido | Formato principal pode ficar inviável | Spike; plano B via PDF exportado |
| Usuário sem a edição Pro do app original | Plano B bloqueado | Perguntar antes; considerar fornecer o PDF por outra via |
| PDFs irregulares sem IA | Muitas questões mal extraídas | Revisão manual forte; testes de regressão de extração |
| Tipos avançados dominando os simulados | MVP cobre pouco | Cartão de referência; subir tipos avançados |
| Risco legal: engenharia reversa e conteúdo vazado | Conflito com licenças | Sem DRM, sem dumps, atestado de direito de uso; decisão do usuário (não é aconselhamento jurídico) |
| Nota escalonada não linear | Estimativa enganosa | Percentual real + estimativa rotulada |
| Perfis de exame desatualizados | Dados errados | Só com fonte oficial conferida |
| Arquivos enviados maliciosos | Segurança | Subprocesso com limites, sem rede; testes de segurança |
| Fixtures sintéticas não representarem os PDFs reais | Testes verdes, produto ruim | Suíte local opcional com `samples/`; cada falha real vira fixture |

## 8. Perguntas em aberto

1. Os `.vce` têm senha ou foram comprados/licenciados? Há a edição Pro do app original?
2. Quais outros formatos existem (ProfExam, Boson, Excel, Word, Moodle)?
3. Que tipos de questão dominam os simulados?
4. Aceitar "VCE → PDF no app original → GOTCHA" como caminho principal?
5. Uso pessoal ou multiusuário? Onde hospedar?
6. Confirmação final: nenhuma IA em nenhuma etapa.

## 9. Fontes a conferir

- Termos da Avanset: https://www.avanset.com/terms-and-conditions.html (não lidos).
- Aposentadoria do AZ-800/AZ-801: https://learn.microsoft.com/credentials/retired-certification-exams.
- ProfExam, Boson ExSim e Anki: capacidades de importação/exportação não verificadas.
