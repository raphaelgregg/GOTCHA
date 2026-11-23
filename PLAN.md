# PLAN — GOTCHA

Plano de implementação. Escopo e decisões vêm do planejamento original (versão 2, sem IA). Este documento foi reconstruído a partir do resumo daquele planejamento; ajuste-o onde divergir do original.

## 1. Objetivo

Permitir que o usuário envie arquivos de simulado em vários formatos, revise as questões importadas e treine com exames cronometrados.

**Critério de sucesso:** arquivo de simulado → revisão → exame cronometrado.

**Fora de escopo:** geração de conteúdo por IA, quebra de proteção/DRM, conteúdo de exame embutido, compartilhamento de bancos entre contas.

## 2. Decisões arquiteturais

| # | Decisão | Motivo |
| --- | --- | --- |
| 1 | Monólito modular com Docker Compose | Simplicidade operacional em um VPS único |
| 2 | React + Vite (SPA) e FastAPI | Stack conhecida, separação clara |
| 3 | PostgreSQL como único armazenamento, inclusive fila de jobs | Evita Redis/broker extra |
| 4 | Importadores como plugins que detectam o formato pelo conteúdo | A extensão `.vce` é ambígua; extensões enganam |
| 5 | Importação grava só rascunhos; confirmar o lote cria questões, com desfazer | Nada entra no banco sem revisão humana |
| 6 | Tipos de questão como plugins (componente, corretor, validação) | Permite adicionar tipos no release 2 sem reescrever |
| 7 | Servidor decide tempo e correção; gabarito não sai antes da hora | Integridade do exame |
| 8 | `pdfplumber` + `pypdfium2`, sem PyMuPDF | PyMuPDF é AGPL e atrapalha serviço hospedado |
| 9 | Worker de importação em subprocesso com limites e sem rede | Arquivos enviados são não confiáveis |
| 10 | Nenhuma biblioteca de IA; CI falha se aparecer uma | Garante o princípio "sem IA" |
| 11 | Perfis de exame são dados, não código | Exames mudam e são aposentados (ex.: AZ-800/801 → AZ-802) |
| 12 | Multiusuário com dados isolados por usuário | Premissa assumida; confirmar |

Todas as decisões ficam como **Proposta** até a aprovação do usuário.

## 3. Fases

### Fase 0 — Spike (3 a 5 dias, bloqueia a Fase 1)

1. Obter arquivos reais: 3 a 5 `.vce` e 3 a 5 PDFs de simulado, de origens e versões diferentes, em `samples/` (ignorada pelo git).
2. VCE: classificar cada arquivo e escolher o resultado:
   - (a) suporte direto às variantes legíveis;
   - (b) somente via PDF exportado pelo aplicativo original;
   - (c) inviável.
3. PDF: comparar `pdfplumber` e `pypdfium2` e medir a taxa de questões extraídas corretamente.
4. Gate de qualidade: só avançar para a Fase 1 com a extração de PDF e o resultado do VCE definidos.

Arquivo protegido é recusado com orientação de exportar pelo app original. Não implementar quebra de senha, criptografia ou DRM.

### Fase 1 — MVP

Formatos: JSON do app, CSV/XLSX (mapeamento de colunas), PDF com texto e imagens. Tipos pontuados: múltipla escolha, múltipla resposta, verdadeiro/falso. Outros tipos viram "cartão de referência" (visível, não pontua, fora dos exames) ou são ignorados, à escolha do usuário.

Blocos de trabalho:

1. Fundação: scaffold, CI, modelo de dados, autenticação, isolamento por usuário.
2. Importação: interface de plugin, upload múltiplo, lote por arquivo, fila de jobs, worker sem rede, importadores do MVP.
3. Revisão: rascunhos, dividir, mesclar, reatribuir alternativas e gabarito, confirmar lote, desfazer.
4. Exame: perfis como dados, exame cronometrado, correção no servidor, resultado com percentual real e estimativa rotulada.
5. Conformidade: atestado de direito de uso no upload, regras de não compartilhamento.

### Fase 2 — Release 2

- VCE direto, se aprovado no spike (plugin experimental).
- HTML, OCR, DOCX, Aiken/GIFT, Moodle XML, QTI.
- Tipos avançados: arrastar-e-soltar, Sim/Não, hot area, estudo de caso. Se os exemplos do usuário forem dominados por esses tipos, subir para o MVP.

## 4. Estimativas

| Escopo | Esforço (dias úteis, 1 pessoa) |
| --- | --- |
| MVP sem VCE direto | 58 a 87 |
| VCE direto (adicional, se aprovado) | 8 a 25 |

As faixas são largas por causa de PDF irregular e VCE. O spike existe para estreitá-las.

## 5. Riscos

| Risco | Impacto | Mitigação |
| --- | --- | --- |
| VCE fechado/protegido | Formato principal pode ficar inviável | Spike com arquivos reais; plano B via PDF exportado |
| PDFs irregulares sem IA para consertar | Muitas questões mal extraídas | Revisão manual forte (dividir, mesclar, reatribuir) |
| Simulados reais cheios de tipos avançados | MVP cobre pouco do conteúdo | Cartão de referência; subir tipos avançados se necessário |
| Risco legal: engenharia reversa e conteúdo vazado | Conflito com licenças | Sem DRM, sem dumps embutidos, atestado de direito de uso; decisão do usuário (não é aconselhamento jurídico) |
| Nota escalonada não linear | Estimativa enganosa | Mostrar percentual real e estimativa rotulada |
| Dados de exame desatualizados | Perfis errados | Só cadastrar com fonte oficial conferida |
| Arquivos enviados maliciosos | Segurança | Subprocesso com limites e sem rede |

## 6. Perguntas em aberto

1. Os `.vce` têm senha ou foram comprados/licenciados?
2. Quais outros formatos existem (ProfExam, Boson, Excel, Word, Moodle)?
3. Há muitas questões de arrastar-e-soltar, Sim/Não, hot area ou estudo de caso?
4. Uso pessoal ou multiusuário?
5. Onde hospedar?
6. Confirmação final: nenhuma IA em nenhuma etapa, inclusive para consertar PDFs?

## 7. Fontes a conferir

- Aposentadoria do AZ-800/AZ-801 e substituição pelo AZ-802: conferir em https://learn.microsoft.com/credentials/retired-certification-exams.
- Que o aplicativo da Avanset exporta PDF: dado de busca, ainda não confirmado.
