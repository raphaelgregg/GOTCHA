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
