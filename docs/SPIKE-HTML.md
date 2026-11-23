# Spike HTML — amostra de página salva (estilo ExamTopics)

Fase 0 do `PLAN.md`. Escopo: avaliar a **estrutura** de uma página HTML de exame salva pelo usuário, para decidir se um importador de HTML é viável. A análise usou contagens e padrões; este documento não reproduz nenhuma questão, alternativa ou gabarito. A página fica fora do repositório.

## Amostra

Uma página salva de um site que publica perguntas de exame (AZ-800, página 1), com 384 KB, UTF-8, 80 scripts e 84 imagens.

## Achados

| Item | Resultado |
| --- | --- |
| Questões na página | **50**, cada uma em um contêiner `exam-question-card` com cabeçalho ("Question #") e corpo |
| Estrutura estável | Classes consistentes: `question-body`, `question-choices-container`, `multi-choice-item` (com `data-choice-letter`), `correct-answer`, `answer-description` |
| Com alternativas listadas | **25** (de 2 a 6 alternativas; 15 delas com 4) |
| Sem alternativas | **25**; a resposta correta é uma **imagem** |
| Provável arrastar-e-soltar, hot area ou Sim/Não | 20 dos 25 sem alternativas, pela heurística de texto |
| Resposta correta nas que têm alternativas | Letras: 24 com 1 letra, **1 com 2 ou mais** letras |
| Imagens no enunciado | 33 questões; 78 imagens no total entre enunciado e resposta |
| Dados extras | Votos da comunidade, "resposta mais votada" (25 questões) e discussão |

## Problema encontrado

**As imagens são caminhos relativos** para uma pasta de arquivos da página salva, que **não veio junto**. Sem essa pasta, não há como recuperar exhibits nem as respostas que são imagem. Para importar a página completa, o usuário precisa enviar a página **com a pasta de recursos** (um .zip dela) ou salvá-la como arquivo único (por exemplo, MHTML ou HTML com imagens embutidas).

## Avaliação

| Item | Estimativa | Observação |
| --- | --- | --- |
| Extrair as 25 questões com alternativas (múltipla escolha e múltipla resposta) | **85 a 90%** | Estrutura previsível; extração por seletores é determinística |
| Cobertura total desta página | **≈ 50%** das questões pontuáveis no MVP | A outra metade é de tipos interativos, que só viram cartão de referência |
| Estabilidade no tempo | **Média** | Depende das classes CSS do site, que podem mudar; cada mudança vira um caso de teste |
| Importar o HTML sem a pasta de imagens | Parcial | Texto funciona; exhibits e respostas em imagem se perdem |

Observação de domínio: a "resposta correta" publicada pelo site e a "mais votada" pela comunidade podem divergir. O importador deve guardar a resposta publicada e sinalizar a divergência na revisão, sem decidir por conta própria.

## Impacto no plano (proposta, depende da sua decisão)

1. **Subir "HTML salvo" do Release 2 para o MVP.** É um formato que o usuário já tem, a extração é mais previsível que a de PDF e serve de segunda fonte além do VCE. Custo estimado: **4 a 8 dias úteis**, com testes primeiro.
2. **Tipos interativos** (arrastar-e-soltar, hot area, Sim/Não) respondem por metade da amostra. Isso reforça a pergunta aberta sobre subir esses tipos ao MVP.
3. **Aceitar ZIP** (página + pasta de recursos) como entrada, além de arquivo único.

## Testes a escrever primeiro (fixtures sintéticas)

- Contêiner com 4 alternativas e resposta de 1 letra → questão de múltipla escolha correta.
- Resposta com 2 ou mais letras → múltipla resposta, com a quantidade exata.
- Cartão sem alternativas e resposta em imagem → cartão de referência, não pontuado, com aviso.
- Imagem referenciada por caminho relativo sem a pasta presente → questão marcada como "anexo ausente".
- HTML do enunciado contendo `<script>` → removido na sanitização.
- Página sem nenhum contêiner de questão → recusada com mensagem clara.

As fixtures serão escritas à mão, imitando só a **forma** da estrutura, sem texto do site.

## Observação sobre origem e direitos

O conteúdo vem de um site de terceiros que publica perguntas de exames reais. Não sei sob que licença ou autorização elas são publicadas. As regras do produto continuam: nada embutido no repositório, nada compartilhado, aviso de direito de uso no primeiro uso. A decisão sobre o que importar é do usuário.

## Segunda rodada: páginas 2 e 3 e um TXT convertido por IA

Foram recebidas as páginas 2 e 3 do mesmo site e um `.txt` que parece ser a página 2 (tópico 2, questões 1 a 24) convertida e traduzida para português por uma ferramenta de IA externa. A análise comparou estrutura, contagens e letras de resposta. **Não** comparou a fidelidade da tradução do texto.

### As três páginas HTML

| Página | Cartões | Tópicos presentes | Com alternativas | Resposta em imagem |
| --- | --- | --- | --- | --- |
| 1 | 50 | 1 | 25 | 25 |
| 2 | 50 | 1 (26) e 2 (24) | 23 | 27 |
| 3 | 50 | 2 (11) e 3 (39) | 23 | 27 |
| **Total** | **150** | | **71 (47%)** | **79 (53%)** |

- **A numeração reinicia por tópico.** A página 2 vai da questão 51 a 76 do tópico 1 e da 1 a 24 do tópico 2; a página 3 mistura os tópicos 2 e 3. Um exame se espalha por várias páginas, e a chave de uma questão é **(tópico, número)**.
- **Só 47% das questões têm alternativas.** As demais dependem de imagem (arrastar-e-soltar, hot area, simulação) e, no MVP planejado, viram cartão de referência. Para este tipo de fonte, isso deixa **mais da metade do exame fora da pontuação**.

### O TXT convertido (24 questões)

| Item | Resultado |
| --- | --- |
| Tipos | 10 múltipla escolha, 7 hot area, 1 arrastar-e-soltar, 3 simulações, 3 estudos de caso |
| Questões com resposta em letras | 13 (as 10 de múltipla escolha e as 3 de estudo de caso) |
| Marcadas como "configuração manual" | 11 de 24 (46%) |
| Marcadores de imagem ausente | 23, em 5 questões |
| Comparação com o HTML original | **13 de 13** respostas em letras iguais; mesmo número de alternativas em todas; tipo (alternativas ou imagem) coincide nas 24 |
| Estudo de caso | O texto do caso é **repetido por inteiro** em cada uma das 3 questões |
| Acentos | Ausentes (texto sem acentuação), o que indica perda de codificação |

Limites: a checagem cobre letras de resposta, contagem de alternativas e tipo. Erros de tradução no enunciado ou nas alternativas **não foram verificados**.

### Impacto no plano (propostas, dependem da sua decisão)

1. **Chave de questão e exame multipágina:** importar várias páginas e juntá-las em um mesmo exame na confirmação do lote, com deduplicação por (tópico, número).
2. **Estudo de caso como entidade própria:** guardar o contexto uma vez e referenciá-lo nas questões, em vez de repetir o texto.
3. **Plugin de TXT simples** (`Q<n>`, alternativas `A.`, `Answer:`): formato determinístico e fácil de testar. Deve aceitar linhas indentadas, mapear `[INSERIR IMAGEM...]` para "anexo ausente" e `[CONFIGURAÇÃO MANUAL...]` para cartão de referência. Não pode presumir acentuação.
4. **Modo "revelar e autoavaliar" para tipos interativos:** mostra o enunciado e o exhibit; o usuário revela a imagem da resposta e marca se acertou. Não exige motor de correção e torna utilizável a metade do exame que hoje ficaria de fora, **desde que as imagens estejam presentes**.
5. **Entrada com imagens:** reforça a necessidade de aceitar ZIP (página + pasta de recursos) ou página de arquivo único.
6. **Texto convertido por IA:** o produto continua sem IA, mas o usuário pode alimentá-lo com texto convertido fora dele. Recomendação: preferir o HTML original e tratar o TXT como alternativa, avisando na revisão que a origem pode conter erros de conversão.

### Testes a acrescentar (fixtures sintéticas)

- Duas páginas que se sobrepõem em (tópico, número) → deduplicadas ao agrupar no mesmo exame.
- Numeração reiniciada em novo tópico → questões distintas, sem colisão.
- Estudo de caso com contexto repetido em três questões → um único contexto compartilhado.
- TXT com respostas indentadas → lidas corretamente.
- TXT com marcador de configuração manual → cartão de referência, não pontuado.
