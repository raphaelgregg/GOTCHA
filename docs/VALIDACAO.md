# Validação da ideia e classificação das funcionalidades

Escopo: validar a ideia contra sistemas similares, tendo o **VCE** como base, estimar a taxa de sucesso e classificar o que é viável. **Nenhuma implementação foi iniciada.**

## 1. Como ler as taxas de sucesso

As porcentagens abaixo são **estimativas de julgamento**, baseadas na pesquisa da seção 2 e em conhecimento geral. **Não foram medidas.** Nenhum arquivo `.vce` ou PDF real foi testado. A Fase 0 (spike) existe para trocar estimativa por medição. Definição usada:

> **Taxa de sucesso** = probabilidade de a funcionalidade atingir seu critério de aceitação com os arquivos reais do usuário, dentro do prazo estimado.

## 2. Sistemas similares e o que ensinam

### Verificado por pesquisa nesta sessão

| Sistema | O que mostra | Lição para o GOTCHA |
| --- | --- | --- |
| **VCE Exam Simulator / Designer (Avanset)** | `.vce` é formato proprietário e fechado; a versão atual é a 2.9.3 (fev/2025); o demo para Windows expõe só as 5 primeiras questões de cada exame ([fonte](https://softradar.com/vce-exam-simulator/2.9.3/), [Make Tech Easier](https://maketecheasier.com/best-software-convert-vce-to-pdf)) | O caminho mais realista é **exportar do app original**; converter exige a edição paga (Pro) |
| **Conversores VCE→PDF** | Todos dependem de abrir o arquivo no app da Avanset e "imprimir" para PDF. Um impressor PDF sozinho não lê VCE ([Make Tech Easier](https://maketecheasier.com/best-software-convert-vce-to-pdf), [iTechGuides](https://www.itechguides.com/7-best-vce-to-pdf-converter-tools-for-converting-vce-files/)) | Ninguém tem parser público; o PDF é o formato de troca de fato |
| **Exam Formatter** | Faz o caminho inverso: importa PDF e gera formato legível pelo VCE Designer | Confirma que **PDF de simulado → questões estruturadas** é um problema que o mercado já resolve por parsing de texto |
| **Open Exam Suite** | Citado como substituto de código aberto do VCE ([SourceForge](https://www.sourceforge.net/directory/?q=vce+file)) | Existe demanda por alternativa aberta; não achei evidência de que leia `.vce` |
| **Parsers de VCE** | Busca no GitHub/SourceForge só retornou formatos homônimos (Valve Choreography Events, firmware AMD) ([Valve](https://developer.valvesoftware.com/wiki/VCE), [CodeProject](https://www.codeproject.com:443/Questions/1060412/answer)) | **Não há parser aberto de VCE conhecido.** Sem especificação, leitura exige engenharia reversa |
| **Moodle** | Importa Aiken (texto simples), GIFT (texto rico), Moodle XML (o mais completo) e formatos Blackboard/QTI ([Moodle docs](https://docs.moodle.org/test/Question_import)) | Aiken/GIFT/Moodle XML são **formatos abertos, documentados e testáveis**: ótimos para a Fase 2 |

### Não verificado nesta sessão

A busca por ProfExam, Boson ExSim e Anki não retornou resultados úteis. O que segue é conhecimento geral e **deve ser conferido**:

- **ProfExam e similares** são players de simulado concorrentes do VCE. Se leem `.vce` é questão em aberto.
- **Boson ExSim** usa formato próprio, também fechado.
- **Anki** importa texto/CSV e exporta pacote próprio; é referência para revisão espaçada, não para simulado cronometrado.

### Questão legal (não é aconselhamento jurídico)

A busca não localizou o texto dos termos da Avanset sobre engenharia reversa. Os termos estão em [avanset.com/terms-and-conditions.html](https://www.avanset.com/terms-and-conditions.html) e precisam ser lidos. Há relatos não verificados de que muitos `.vce` em circulação são conteúdo de exame vazado ("dumps"), o que reforça as regras do produto: sem dumps embutidos, sem compartilhamento de bancos e um aviso de direito de uso no primeiro uso.

## 3. Taxa de sucesso estimada

| Item | Estimativa | Principal incerteza |
| --- | --- | --- |
| Motor de exame cronometrado (tempo e correção no servidor) | **95%** | Baixa: problema conhecido |
| Importar JSON do app / CSV / XLSX | **90 a 95%** | Variedade de colunas, resolvida pelo mapeamento |
| Importar PDF com texto (extração + revisão manual) | **80 a 85%** utilizável após revisão; **60 a 75%** das questões corretas **sem** revisão | Layouts irregulares e alternativas quebradas entre páginas; sem IA para corrigir |
| PDF com imagens nas questões | **65 a 75%** | Associar imagem à questão certa |
| Aiken / GIFT / Moodle XML (Fase 2) | **90%** | Formatos abertos e documentados |
| **VCE direto (ler o `.vce`)** | **10 a 20%** | Formato fechado, sem especificação pública nem parser aberto, provável criptografia, risco legal |
| **VCE via PDF exportado do app original** | **45 a 60%** | Usuário precisar da edição Pro; perda de tipos interativos; qualidade da impressão |
| **Objetivo do usuário: "meus `.vce` viram exames"** (qualquer caminho) | **≈ 50 a 60%** | Depende quase inteiramente do spike |
| **Produto sem VCE (JSON/CSV/PDF → revisão → exame)** | **≈ 85%** | Qualidade da extração de PDF |

**Leitura:** a ideia como produto é viável (~85%). O ponto de maior risco é exatamente a premissa de partida, o VCE. A decisão de arquitetura (plugins de formato, PDF como formato universal de entrada) mantém o projeto útil mesmo que o VCE direto falhe.

### Como a estimativa do VCE foi composta

`P(qualquer caminho) = P(direto) + (1 − P(direto)) × P(PDF exportado)` com P(direto) ≈ 0,15 e P(PDF) ≈ 0,5 resulta em ≈ 0,58. Os valores são julgamentos, não dados.

## 4. Classificação das ideias

Critérios: **Viabilidade** (técnica), **Valor** (para o objetivo), **Risco** (técnico/legal). Camadas: **A** MVP · **B** Release 2 · **C** condicional (depende do spike ou de decisão) · **D** descartada.

| Ideia | Camada | Viabilidade | Valor | Risco | Observação |
| --- | --- | --- | --- | --- | --- |
| Exame cronometrado (modo prova) com correção no servidor | A | Alta | Alto | Baixo | Núcleo do produto |
| Modo estudo (feedback imediato) vs. modo prova | A | Alta | Alto | Baixo | Barato; mesmo motor |
| Marcar questão para revisão, navegar, pausar | A | Alta | Médio | Baixo | Padrão em simuladores |
| Importar JSON do app | A | Alta | Médio | Baixo | Também serve de backup/exportação |
| Importar CSV/XLSX com mapeamento de colunas | A | Alta | Alto | Baixo | Fonte comum de bancos próprios |
| Importar PDF com texto | A | Média | Alto | Médio | Caminho universal, inclusive para VCE exportado |
| Imagens em questões (PDF) | A | Média | Médio | Médio | Associação imagem↔questão |
| Rascunhos + revisão + desfazer | A | Alta | Alto | Baixo | Compensa a ausência de IA |
| Ferramentas de revisão: dividir, mesclar, reatribuir | A | Alta | Alto | Baixo | Obrigatórias |
| Tipos: múltipla escolha, múltipla resposta, V/F | A | Alta | Alto | Baixo | Cobrem boa parte dos bancos |
| Cartão de referência para tipos não pontuados | A | Alta | Médio | Baixo | Evita descartar conteúdo |
| Perfis de exame como dados | A | Alta | Médio | Baixo | Só com fonte oficial |
| Exportar o banco (JSON/CSV) | A | Alta | Médio | Baixo | Reduz lock-in |
| Aviso de direito de uso no primeiro uso | A | Alta | Baixo | Baixo | Para uso pessoal basta um aviso |
| Percentual real + estimativa de nota escalonada rotulada | A | Média | Médio | Médio | Nunca prometer a nota oficial |
| Aiken, GIFT, Moodle XML | B | Alta | Médio | Baixo | Formatos abertos |
| DOCX | B | Média | Médio | Médio | Parsing de estrutura |
| **HTML salvo (questões com alternativas), TXT simples** | A | Alta | Alto | Baixo | Amostras reais recebidas (`docs/SPIKE-HTML.md`); HTML é frágil a mudanças no site |
| **Exame multipágina com deduplicação; estudo de caso compartilhado** | A | Alta | Alto | Baixo | Numeração reinicia por tópico |
| **Gerador de simulado a partir do banco** | A | Alta | Alto | Baixo | Sorteio por semente; sem IA |
| QTI | B | Média | Baixo | Médio | Poucos usuários prováveis |
| OCR (PDF escaneado) | B | Média | Médio | Alto | Subprocesso com limites; qualidade variável |
| Estatísticas por tema/ponto fraco | B | Alta | Alto | Baixo | Depende de tags nas questões |
| Revisão espaçada de erradas (estilo Anki) | B | Alta | Médio | Baixo | Extra |
| Arrastar-e-soltar, Sim/Não, hot area, simulação: **importar com autoavaliação** | A | Média | Alto | Médio | ~metade das amostras; exige as imagens junto |
| Correção automática desses tipos | B | Baixa | Médio | Alto | Exige motor próprio por tipo |
| **VCE via PDF exportado** | C | Média | Alto | Médio | Sem trabalho extra além do PDF; exige Pro no app original |
| **VCE direto** | C | Baixa | Alto | **Alto** | Só se o spike achar variante legível e o aspecto legal permitir |
| PWA offline | C | Média | Baixo | Baixo | Só se houver demanda |
| Simulações de laboratório | D | Baixa | Médio | Alto | Fora de escopo |
| Geração de questões por IA | D | n/a | n/a | n/a | Descartada pelo usuário |
| Quebra de senha/DRM de `.vce` | D | n/a | n/a | Legal | Não será implementada |
| Compartilhar ou publicar bancos de simulados | D | Média | Médio | Legal | Incentiva dumps; fora do escopo pessoal |
| Conteúdo de exame embutido | D | n/a | n/a | Legal | Contraria a regra do produto |

## 5. Pontos que o usuário precisa decidir

1. Os `.vce` são protegidos? Foram comprados/licenciados? Há a edição Pro do app original?
2. Quais tipos de questão dominam os simulados? (decide se a camada B de tipos avançados sobe)
3. Aceitar o caminho "VCE → PDF no app original → GOTCHA" como solução principal?
4. Leitura dos termos da Avanset antes de qualquer trabalho de engenharia reversa.

## Fontes

- [VCE Exam Simulator 2.9.3 (SoftRadar)](https://softradar.com/vce-exam-simulator/2.9.3/)
- [Best Software to Convert VCE to PDF Files (Make Tech Easier)](https://maketecheasier.com/best-software-convert-vce-to-pdf)
- [7 best VCE to PDF converter tools (iTechGuides)](https://www.itechguides.com/7-best-vce-to-pdf-converter-tools-for-converting-vce-files/)
- [Open source projects for "vce file" (SourceForge)](https://www.sourceforge.net/directory/?q=vce+file)
- [VCE (Valve Choreography Events), formato homônimo](https://developer.valvesoftware.com/wiki/VCE)
- [Resposta no CodeProject sobre ler formato sem especificação](https://www.codeproject.com:443/Questions/1060412/answer)
- [Importação de questões no Moodle](https://docs.moodle.org/test/Question_import)
- [Termos da Avanset (não lidos nesta sessão)](https://www.avanset.com/terms-and-conditions.html)
