# Spike PDF — amostra AZ-140 (762 páginas)

Fase 0 do `PLAN.md`. Escopo: medir se um PDF de simulado pode ser lido de forma determinística (sem IA). A análise usou contagens, padrões e validações estruturais. Este documento não reproduz nenhuma questão, alternativa, gabarito ou comentário. O arquivo fica fora do repositório.

## Amostra

| Item | Valor |
| --- | --- |
| Páginas / tamanho | 762 / 18,8 MB (A4) |
| Gerador | **WeasyPrint 61.2** (HTML convertido em PDF), título "SecExams" |
| Texto | Selecionável em todas as páginas (só a capa não tem texto útil); não criptografado |
| Imagens | 2 025 no total |

Trata-se de um PDF **gerado a partir de página web**, com texto limpo. Um PDF exportado de um `.vce` ou digitalizado pode se comportar diferente. Esta é a única amostra de PDF até agora.

## Estrutura encontrada

Cada questão segue um padrão estável:

`Question #N` → tipo opcional (`HOTSPOT -`, `DRAG DROP -`) → enunciado → alternativas (`A)` a `F)`) → `Explanation` → `Correct Answer:` → `Reference:` (opcional) → `Community Discussion` (comentários de usuários).

Em cada página há cabeçalho repetido, rodapé "Page X of 762" e um índice no início.

## Resultados

| Medida | Resultado |
| --- | --- |
| Questões detectadas | **341**, numeradas de 1 a 341, sem repetição |
| Múltipla escolha ou resposta (com alternativas) | 193 por heurística de tipo; **216** têm resposta em letras |
| Hot area | 90 |
| Arrastar-e-soltar | 29 |
| Estudo de caso | 29 |
| Resposta correta em letras | **216 (63%)** |
| Resposta correta **sem letras** (imagem) | **125 (37%)** |
| Validação estrutural das 216 com letras | **216 de 216 (100%)**: alternativas A, B, C… contíguas, sem repetição, e a resposta contida nas alternativas |
| Alternativas por questão | 2 (29), 3 (4), 4 (134), 5 (41), 6 (8) |
| Com `Reference:` | 108 |
| Com `Community Discussion` | **341 (todas)** |

A validação estrutural mostra que o texto foi **segmentado corretamente**. Ela **não** prova que o conteúdo ou o gabarito estejam certos.

### Bibliotecas

| | `pypdfium2` | `pdfplumber` |
| --- | --- | --- |
| Tempo | 2,6 s para o PDF inteiro (texto e imagens) | 2,5 s para 40 páginas (≈ 10 vezes mais lento) |
| Texto | Mesmo tamanho nas páginas comparadas | Mesmo tamanho; similaridade de 0,94 em média, o que indica **diferença na ordem das linhas**, não perda de conteúdo (causa não investigada) |

Para esta amostra, `pypdfium2` serve como extrator principal. O `pdfplumber` fica para tabelas e coordenadas, onde a ordem importa.

### Imagens

- Cerca de **1 523** imagens (≈ 50 × 200 pt, 2 por página) são decorativas e se repetem em todas as páginas. Devem ser filtradas por repetição.
- Cerca de **480** imagens são de conteúdo (exhibits e imagens de resposta), com tamanhos variados.
- As 125 questões sem letras têm a resposta em **imagem**, como nas páginas HTML.

## Avaliação

| Item | Estimativa | Observação |
| --- | --- | --- |
| Segmentar questões e alternativas deste tipo de PDF | **90 a 95%** | 100% de validade estrutural nesta amostra, mas é uma amostra só |
| Extrair imagens e associá-las à questão certa | 75 a 85% | Exige coordenadas e filtro de imagens decorativas |
| Generalizar para PDFs de outros geradores (inclusive exportados do VCE) | **Desconhecido** | Precisa de mais amostras |
| Cobertura pontuável sem imagens | 63% | O resto depende de autoavaliação com imagem |

## Impactos no plano

1. **O importador de PDF é viável** para PDFs com texto gerados de páginas web. Isso reduz o risco do maior ponto de incerteza.
2. **Descartar a seção de comentários:** `Community Discussion` aparece em todas as questões e é texto de terceiros. Deve ser ignorada por padrão, e guardada como nota só se o usuário optar.
3. **Remover cabeçalho, rodapé e índice** antes de segmentar, e filtrar imagens repetidas.
4. **Quase 40% sem letras:** reforça o modo "revelar e autoavaliar".
5. **O PDF é um bom formato universal:** a mesma estrutura de campos (`Question #`, `Correct Answer:`, `Explanation`) aparece no HTML e no TXT, o que permite um modelo interno comum.
6. **Tempo:** 762 páginas em poucos segundos; não exige fila longa, mas a importação continua em subprocesso por segurança.

## Testes a escrever primeiro (fixtures sintéticas)

- Bloco com cabeçalho, 4 alternativas e `Correct Answer:` com 1 letra → múltipla escolha.
- `Correct Answer:` com 2 ou mais letras → múltipla resposta com quantidade exata.
- `Correct Answer:` sem letras → questão interativa com imagem de resposta, ou "anexo ausente".
- Texto do enunciado contendo "A." no início de uma linha → não vira alternativa.
- Cabeçalho e rodapé repetidos no meio do enunciado → removidos sem cortar a questão.
- Seção `Community Discussion` → ignorada.
- Imagem repetida em todas as páginas → filtrada como decorativa.
- Numeração com salto ou repetição → sinalizada na revisão.
- PDF digitalizado (sem texto) → recusado com orientação, até existir OCR.

As fixtures serão escritas à mão, imitando só a **forma** da estrutura.

## Origem e direitos

O PDF vem de um site de terceiros que publica perguntas de exame reais. Não sei sob que autorização. As regras do produto continuam: nada embutido no repositório, nada compartilhado, aviso no primeiro uso. A decisão sobre o que importar é do usuário.
