# Arquitetura: questões multimídia, tipos interativos e formato `.gotcha`

Entrega técnica do requisito adicional (item 14). **Nenhum código foi escrito para este requisito.** O documento descreve o desenho, as decisões, os testes e os pontos que precisam da sua confirmação. Estimativas e taxas de sucesso são julgamentos, não medições.

## 1. Pontos que mudam o desenho (leia primeiro)

1. **O que as amostras permitem importar automaticamente é menos do que o requisito pede.** Nas páginas HTML e no PDF recebidos, as questões de Hot Area, Drag and Drop e simulação chegam como **enunciado + imagem** (a área de resposta é uma figura). Não há regiões, itens nem posições no arquivo. Reconstruir regiões clicáveis ou itens arrastáveis exige **autoria manual no editor**, e eu não vou fingir que a importação faz isso. Sem IA, não há como inferir geometria de uma imagem.
2. **Precisamos de um tipo de transição.** Hoje existe `interactive` (autoavaliada). Proponho mantê-lo como tipo `self_assessed` ("resposta em imagem"), para que as questões importadas que ainda não foram reconstruídas continuem utilizáveis e possam ser **convertidas depois, no editor**, para Hot Area, Drag and Drop etc. Ele não está na sua lista de 8 tipos; preciso da sua aprovação.
3. **"Hot Area" tem dois significados.** No requisito é *região clicável sobre imagem*. Nos exames Microsoft das amostras, "Hot Area" costuma ser uma lista de afirmações com **menus suspensos** ("selecione na área de resposta"). Esse segundo caso se modela melhor com o **Active Screen** (componentes `select`). Vou suportar o primeiro em `hot_area` e o segundo como um modelo pronto de `active_screen`, salvo se você preferir outro caminho.
4. **VCE e "INDEX".** O VCE continua **não sendo decodificado** (regra 5 do projeto): só entra por PDF/HTML exportados. Não conheço um formato "INDEX"; preciso que você diga o que é e traga uma amostra.
5. **"Formato proprietário `.gotcha`".** Proponho um **pacote ZIP com JSON e mídia**, com especificação aberta e documentada. "Proprietário" aqui significa "do GOTCHA", sem criptografia nem ofuscação, de acordo com a regra de não proteger formatos.

## 2. Princípios

- O motor de questões é independente do formato de origem: toda importação converge para o **modelo canônico** (seção 4).
- Cada tipo tem **modelo, validador, renderizador, editor, mecanismo de resposta, corretor e serializador próprios** (seção 5). Nada de múltipla escolha disfarçada.
- **Nada é descartado em silêncio**: tudo que não foi preservado vira aviso de conversão com o trecho original guardado (seção 9).
- **Local-first e custo zero**: sem nuvem, sem serviço pago, dependências de código aberto, tudo no disco do usuário.
- **O gabarito nunca vai para a interface em modo prova**, para nenhum tipo (seção 10).

## 3. Formato `.gotcha` (pacote)

ZIP (deflate; mídia já comprimida é armazenada sem recompressão).

```text
exame.gotcha
├── manifest.json            versão do formato, app, id do pacote, título, contagens, SHA-256 de cada arquivo
├── exam.json                nome, tópicos, perfil de exame (dados), ordem das questões
├── cases/<id>.json          estudos de caso (contexto compartilhado)
├── questions/<uid>.json     uma questão por arquivo (modelo canônico)
├── assets/index.json        metadados dos recursos
├── assets/<aa>/<sha256>.<ext>   mídia derivada exibível
└── originals/<sha256>.<ext>     arquivo original, quando difere do exibível (ex.: SVG bruto, PDF)
```

- **Autossuficiente**: nenhuma URL externa. Um validador recusa referências `http(s)://` em qualquer campo.
- **Íntegro**: `manifest.json` lista o SHA-256 de cada arquivo; a importação verifica antes de aceitar.
- **Seguro**: mesmos limites do ZIP atual (tamanho total, número de membros, caminhos suspeitos), sem executar nada do pacote.
- **Versionado**: `format_version` no manifesto e `schema_version` em cada questão; migrações explícitas e testadas.
- **Compatibilidade**: o `gotcha-json` atual (v1) continua legível e é convertido ao importar.

## 4. Modelo canônico de questão

Envelope comum (todos os tipos):

```json
{
  "uid": "q_7f3a…",                  // UUID estável, nunca muda
  "fingerprint": "sha256:…",         // hash do conteúdo normalizado (dedupe)
  "schema_version": 2,
  "type": "hot_area",                // discriminador
  "topic": 1, "number": 12,          // posição de origem, não identidade
  "prompt": [ /* blocos, ver abaixo */ ],
  "explanation": [ /* blocos */ ],
  "case_id": null,
  "scoring": { "mode": "all_or_nothing", "points": 1 },
  "source": { "format": "html", "file": "pagina1.html", "ref": "Topic 1 · Q12" },
  "conversion": { "status": "partial", "preserved": [], "lost": [], "warnings": [] },
  "payload": { /* específico do tipo */ }
}
```

**Blocos de conteúdo** (ordem = ordem de exibição; reposicionar é reordenar):
`paragraph`, `html` (sanitizado), `table`, `code`, `image` (`asset`, `alt`, `width_pct`, `align`, `caption`), `attachment` (`asset`, `label`).
Imagens no enunciado, nas alternativas, nos itens e nas explicações usam o mesmo bloco `image`.

### Payload por tipo

| Tipo | Payload (resumo) | Gabarito |
| --- | --- | --- |
| `multiple_choice` | `options[{id, blocks}]`, `variant: "standard"\|"true_false"` | `correct: option_id` |
| `multiple_select` | `options[...]`, `required_count` | `correct: [option_id]`, pontuação total ou parcial |
| `drag_drop` | `items[{id, blocks, reusable}]`, `targets[{id, blocks, min, max}]`, `background?`, `ordered_targets` | `key: {target_id: [item_id]}` |
| `build_list` | `pool[{id, blocks}]` (inclui distratores), `answer_length` | `sequence: [item_id]`, pontuação total ou por posição |
| `hot_area` | `image{asset, aspect}`, `shapes[{id, kind, geometry}]`, `selection{mode, required_count}` | `correct: [shape_id]` |
| `active_screen` | `screens[...]`, `state`, `start`, `fidelity`, `limitations[]` | `completion` e `checks` (condições) |
| `case_study` | **contêiner**, ver seção 8 | as questões internas têm gabarito próprio |
| `lab` | `mode`, `objectives`, `steps`, `environment`, `completion` | critérios por etapa |
| `self_assessed` (transição) | `answer_images`, instruções | autoavaliação do usuário |

## 5. Arquitetura de plugins por tipo

Cada tipo registra um conjunto **único** de peças, no backend e na interface:

| Peça | Backend (Python) | Interface (React) |
| --- | --- | --- |
| Modelo | classe Pydantic (união discriminada por `type`) | tipo TS gerado do JSON Schema |
| Validador | estrutural (Pydantic) e semântico (ex.: gabarito aponta para ids existentes) | validação no editor |
| Resposta | tipo `Response` do tipo | estado local do componente |
| Corretor | `grade(question, response) -> GradeResult` | — |
| Serializador | `to_package` / `from_package` + migrações | — |
| Renderizador | — | componente de prova e de revisão |
| Editor | — | painel específico dentro do editor universal |
| Exposição | `public_view` sem gabarito | — |

- `GradeResult` generaliza o `Outcome` atual: `{score: 0..1, outcome, detail}`, com crédito parcial opcional.
- Os tipos TS saem do **JSON Schema gerado pelo Pydantic** no build, para backend e interface não divergirem.
- **Suíte de contrato** parametrizada: todo tipo precisa passar por serialização ida e volta, rejeição de payload inválido, corretor com respostas de ouro, `public_view` sem gabarito, renderizador (smoke test) e editor (ida e volta).

## 6. Recursos e imagens

### Modelo de armazenamento

Tabela `assets` (e `assets/index.json` no pacote):

| Campo | Observação |
| --- | --- |
| `id` | `sha256` do conteúdo original (identidade) |
| `original_name`, `names[]` | nomes vistos nas origens |
| `mime` | detectado pelo **conteúdo** |
| `width`, `height`, `pages?` | dimensões (PDF: páginas) |
| `size`, `sha256` | |
| `path` | caminho interno no pacote |
| `default_alt` | descrição alternativa padrão (cada uso pode ter a sua) |
| `origin` | `{format, file, page, bbox}` |
| `conversion` | `{derived_from, operation, lossless, notes}` |

### Identificação e hash

- Identidade = SHA-256 dos bytes originais. Mesma imagem usada em várias questões = **um** recurso, com contagem de referências.
- Reimportação: recursos com o mesmo hash não são duplicados; coleta de recursos órfãos só quando a contagem chega a zero.
- **Sem recompressão automática.** Os bytes originais são preservados. Derivados existem só quando necessários e ficam rotulados:
  - **SVG**: o bruto vai em `originals/` e **nunca é exibido**; a versão sanitizada (sem scripts, `foreignObject`, eventos e referências externas) é um derivado.
  - **PDF anexo**: o original é preservado; páginas renderizadas em PNG sem perda são derivados para exibição.
- Tipos aceitos: PNG, JPEG, WebP, GIF, SVG (sanitizado), PDF e anexos permitidos por lista. Tipo detectado por assinatura, não por extensão.
- Limites: tamanho por recurso e por pacote, número máximo de pixels (proteção contra *decompression bomb*) e rejeição de tipos fora da lista.
- Dimensões: lidas dos cabeçalhos (Pillow, licença permissiva) sem decodificar a imagem inteira.

### Edição de imagens

Visualizar, substituir (mantém o `id` de uso e recalcula o hash), remover, adicionar, reposicionar (reordenar blocos), redimensionar a apresentação (`width_pct`, sem tocar no arquivo), descrição alternativa por uso, e pré-visualização final com o renderizador real.

## 7. Estratégias por tipo

### Hot Area: coordenadas

- Coordenadas **normalizadas** no sistema da imagem: `x`, `y` em `[0, 1]` relativos à largura e à altura naturais.
- `rect {x, y, w, h}`, `circle {cx, cy, r}` com `r` relativo à **largura** (círculo permanece círculo), `polygon {points: [[x, y], …]}` com no mínimo 3 pontos.
- Renderização: sobreposição SVG com `viewBox="0 0 1 aspect"`, onde `aspect = altura / largura`. Funciona em qualquer tamanho de tela.
- Acerto por clique: ponto no retângulo, distância ao centro e *ray casting* para polígono, tudo em espaço normalizado, testado de forma isolada.
- Se a imagem for **substituída** por outra de proporção diferente (> 1%), as regiões são mantidas e a questão é marcada "precisa de revisão".
- Acessibilidade: cada região é focável e acionável pelo teclado; o editor também tem campos numéricos.
- Regras: seleção única ou múltipla, quantidade exata, tudo-ou-nada ou parcial.

### Drag and Drop

- Itens (texto e/ou imagem) e alvos (com mínimo e máximo de itens); itens podem ser reutilizáveis.
- Alvos podem ser regiões sobre uma imagem de fundo (mesma geometria normalizada do Hot Area, reaproveitando o código).
- Correção: compara o conjunto (ou a sequência, se `ordered_targets`) de cada alvo com o gabarito; crédito parcial por alvo, se configurado.
- Interação por ponteiro e **por teclado** (selecionar item, escolher alvo).

### Build List

- A interface recebe o `pool` **embaralhado de forma determinística** (semente da sessão) e monta a lista de resposta.
- Correção por sequência exata ou por posição, com feedback configurável.
- O gabarito (`sequence`) fica no servidor.

### Active Screen: arquitetura segura e declarativa

Nada de HTML ou JavaScript importado. A tela é **dado** interpretado por um motor próprio:

```json
{
  "screens": [{ "id": "s1", "components": [
    {"id": "tab", "type": "tabs", "tabs": [{"id": "t1", "label": "Rede"}]},
    {"id": "ip", "type": "input", "label": "Endereço IP", "bind": "ip"},
    {"id": "go", "type": "button", "label": "Aplicar",
     "on_click": [{"do": "set", "var": "applied", "value": true},
                  {"do": "goto", "screen": "s2"}]}
  ]}],
  "state": {"ip": {"type": "string", "initial": ""}, "applied": {"type": "bool", "initial": false}},
  "start": "s1",
  "completion": {"all": [{"op": "eq", "var": "ip", "value": "10.0.0.5"},
                          {"op": "eq", "var": "applied", "value": true}]},
  "fidelity": "reconstructed",
  "limitations": ["Cores e menus do portal original não foram reproduzidos."]
}
```

- **Componentes permitidos** (lista fechada): texto, imagem, botão, campo de texto/número, seletor (`select`), caixa de seleção, grupo de opções, abas, menu (com subitens), tabela selecionável, alternador. Tipo desconhecido é **rejeitado**.
- **Estado**: variáveis tipadas. **Ações**: `set`, `toggle`, `goto`, `show_message`, `append`. **Condições**: árvore JSON (`eq`, `ne`, `in`, `and`, `or`, `not`), sem avaliação de código (`eval` proibido), sem laços.
- **Limites**: máximo de componentes, profundidade e passos; texto sempre tratado como texto (nunca como HTML).
- **Correção no servidor**: a interface envia o **registro de ações**; o servidor **reexecuta** as ações a partir do estado inicial e avalia `completion` e `checks`. Assim o gabarito não vai ao navegador e o resultado não pode ser forjado.
- **Fidelidade declarada** (`reconstructed`, `approximate`, `screenshot_only`) e `limitations[]` aparecem ao usuário. Interfaces originais **não são importadas**: elas são **construídas** no editor ou a partir de modelos prontos.
- Modelos prontos: formulário com menus suspensos (o "Hot Area" de afirmações da seção 1), assistente por abas, tabela com seleção.

### Case Study

- Entidade `case_study` guardada **uma vez**: `title`, `sections[{id, title, blocks}]` (visão geral, requisitos, ambiente, restrições…), recursos (imagens, tabelas, anexos) e `question_uids` em ordem.
- As questões apontam para o caso por `case_id`; podem ser de **qualquer tipo**.
- Interface: painel com abas por seção, sempre disponível ao lado da questão. O gerador de simulado já mantém as questões de um caso juntas.
- Edição: o contexto é editado em um lugar e vale para todas as questões; cada questão é editada normalmente.

### Lab

`lab.mode` é **obrigatório** e sempre visível na tela:

| Modo | O que é | Pontuação |
| --- | --- | --- |
| `simulated` | roda localmente no motor do Active Screen; **é uma simulação** | automática, avaliada no servidor, **separada** das demais |
| `external_instructions` | instruções para fazer fora do app (por exemplo, em uma máquina virtual do usuário) | **autoavaliada** (checklist) |
| `real` | descreve um ambiente real que o GOTCHA **não executa** | autoavaliada |

- Estrutura: `objectives[]`, `steps[{id, instructions, screens?, checks[]}]`, `resources[]`, `environment{kind, description}`, `completion`.
- A interface exibe uma faixa fixa "Simulação local, não é execução real de Azure/AWS/Cisco" nos laboratórios simulados. O GOTCHA **nunca** provisiona nem acessa infraestrutura de terceiros, mantendo o custo zero.

## 8. Editor universal

Uma única casca, usada para questões de arquivos importados **e** de simulados GOTCHA já salvos:

1. **Enunciado**: editor de blocos (texto, tabela, código, imagem, anexo), com reordenação e pré-visualização.
2. **Mídia**: galeria dos recursos usados, com substituir, remover, adicionar, descrição alternativa, tamanho de apresentação e lista de recursos **órfãos** e **ausentes**.
3. **Painel do tipo** (vem do registro): alternativas e gabarito; **regiões** desenhadas sobre a imagem (retângulo, círculo, polígono, alças, ajuste numérico); itens e alvos; sequência; construtor de telas (árvore de componentes, inspetor de propriedades, estados e ações em formulários, não em código); etapas do laboratório.
4. **Gabarito e critérios** de avaliação.
5. **Prévia** com o mesmo renderizador da prova, em modo de teste.
6. **Conversão de tipo** (por exemplo, de `self_assessed` para `hot_area`), preservando prompt e mídia.

Backend: o endpoint de edição de questão confirmada (`PATCH /api/questions/{uid}`) usa a **mesma** validação do rascunho.

## 9. Preservação durante a conversão

Regra testável: **todo recurso e todo trecho extraído termina em um de três lugares**: anexado a uma questão, na lista de **órfãos** do lote, ou na lista de **não convertidos**. Nada some.

- `conversion` por questão: `status` (`ok`, `partial`, `manual_required`), `preserved[]`, `lost[]`, `warnings[]` e o **trecho original** (texto ou recorte da página) guardado como bloco de apoio.
- Relatório por lote: contagens, imagens sem associação, recursos ausentes, conteúdo não convertido, ordem original mantida.
- **PDF**: extrair imagens embutidas **com a posição** (`pypdfium2`) e associá-las à questão pela faixa vertical entre títulos. Gráficos **vetoriais** (tabelas e diagramas desenhados) não são imagens; para esses, o recorte da região é **renderizado em PNG sem perda** como bloco visual de apoio, e o texto extraído é mantido ao lado.
- **HTML**: imagens vindas do ZIP, tabelas preservadas como `table`, ordem do documento mantida (já parcialmente feito).
- **JSON (v1)** e `.gotcha`: leitura direta.
- **VCE**: não é lido; recusado com orientação. **INDEX**: aguardando definição.
- Ao revisar, o usuário vê os avisos, abre o editor e resolve cada pendência.

## 10. Exposição do gabarito por tipo

| Tipo | O que a interface recebe | O que fica no servidor |
| --- | --- | --- |
| múltipla escolha/seleção | opções e quantidade exigida | gabarito |
| drag and drop | itens e alvos | `key` |
| build list | `pool` embaralhado | `sequence` |
| hot area | imagem e regiões **sem** marcação de corretas | `correct` |
| active screen | telas, estado e ações | `completion` e `checks`; reexecução do registro de ações |
| lab simulado | idem Active Screen | critérios |

Teste de segurança por tipo: o JSON enviado em modo prova não contém nenhum campo de gabarito.

## 11. Reimportação sem duplicar

- Identidade da questão: `uid`. Duplicata de conteúdo: `fingerprint` (hash do conteúdo normalizado, sem posição nem metadados de origem).
- Importar um `.gotcha` passa pelo mesmo fluxo de **rascunho → revisão → confirmação**, com dedupe por `uid`, depois por `fingerprint`, e por (tópico, número) apenas para ordenação.
- Para uma questão já existente: *ignorar*, *substituir* ou *manter as duas* (com o conflito exibido), nunca duplicar em silêncio.
- Recursos são unificados por SHA-256. Relatório: adicionadas, ignoradas, conflitos, recursos reaproveitados.

## 12. Migração do que já existe

| Hoje | Passa a ser |
| --- | --- |
| `single` | `multiple_choice` |
| `multiple` | `multiple_select` |
| `true_false` | `multiple_choice` com `variant = true_false` |
| `interactive` | `self_assessed` (conversível no editor) |
| `ImageRef` (`stem`/`answer`) | blocos `image` e imagens de resposta |
| `stem` HTML | bloco `html` |
| `CaseStudy` | `case_study` ampliado |
| `gotcha-json` v1 | importado e convertido |

Migração de banco com `schema_version` e testes de ida e volta antes e depois.

## 13. Plano de testes (importação, edição, exportação, reimportação)

Todos escritos **antes** do código (TDD). Fixtures sintéticas; amostras reais só em `samples/`.

| # | Critério de aceitação | Teste principal |
| --- | --- | --- |
| 1 | Questão com várias imagens | modelo e renderizador com 3 imagens em posições distintas |
| 2 | Imagem compartilhada | duas questões, um recurso, contagem de referências = 2 |
| 3 | Imagens preservadas após exportar | hash do recurso idêntico antes e depois |
| 4 | `.gotcha` sem arquivos externos | importar com a pasta de origem apagada; validador recusa URL externa |
| 5 | Hot Area após reimportação | as mesmas coordenadas e a mesma correção |
| 6 | Drag and Drop após reimportação | mesmo gabarito e mesma nota |
| 7 | Build List preserva a sequência | `sequence` idêntica e correção por posição |
| 8 | Active Screen preserva estados e interações | reexecução do registro de ações dá o mesmo resultado |
| 9 | Case Study preserva o contexto | contexto único, N questões referenciando |
| 10 | Lab distingue simulação de execução real | `mode` obrigatório, faixa visível, pontuação separada |
| 11 | Edição manual de todos | ida e volta do editor para cada tipo |
| 12 | Reimportação não duplica | importar duas vezes: zero questões e zero recursos novos |
| 13 | Relatório do que não foi preservado | fixtures com imagem órfã, recurso ausente e trecho não convertido, todos listados |

Adicionais:
- **Propriedades** (`hypothesis`): serialização ida e volta de qualquer questão válida; geometria (ponto dentro/fora) coerente entre retângulo, círculo e polígono; sorteio determinístico do Build List.
- **Segurança**: SVG com script sanitizado; recurso fora da lista recusado; ZIP malicioso; interpretador do Active Screen recusa tipo/ação desconhecidos e respeita limites.
- **Contrato** por tipo (seção 5) e **ponta a ponta** com Playwright para Hot Area (desenhar região e responder) e Build List.

## 14. Fases, estimativas e taxas de sucesso

Julgamento, não medição. Dias úteis para uma pessoa, com testes.

| Fase | Conteúdo | Dias | Sucesso |
| --- | --- | --- | --- |
| A | Modelo canônico v2, registro de tipos, loja de recursos com hash, pacote `.gotcha`, migração | 10 a 15 | 90% |
| B | Portar múltipla escolha/seleção; **Build List**; **Drag and Drop**; **Hot Area** com editor de regiões | 20 a 32 | 85% |
| C | **Case Study** como entidade e editor de contexto | 5 a 8 | 90% |
| D | Editor universal (blocos, galeria de mídia, prévia, conversão de tipo) | 12 a 18 | 85% |
| E | Importadores: imagens do PDF com posição, relatório de conversão, órfãos | 12 a 20 | 70 a 80% |
| F | **Active Screen** (motor, validador, construtor visual) | 20 a 35 | 65 a 75% |
| G | **Lab** (reaproveita o motor de F) | 8 a 14 | 60 a 70% |
| | **Total** | **87 a 142** | |

Os pontos de maior risco: o **construtor visual de Active Screen** (escopo elástico) e a **associação de imagens em PDF** (depende do gerador do PDF). Recomendo entregar por fases, na ordem acima, cada uma utilizável por si.

## 15. Custo zero e local-first

Sem serviços externos. Dependências novas previstas: **Pillow** (dimensões e validação de imagem; licença permissiva) e nada além disso no backend. Na interface, arrastar e soltar e geometria com ponteiros e SVG próprios (sem biblioteca paga). O laboratório simulado roda no navegador do usuário.

## 16. Decisões que preciso de você

1. Aprova o tipo de transição **`self_assessed`** para o que já foi importado e ainda não foi reconstruído?
2. **Hot Area**: região clicável sobre imagem (como no requisito) e, **além disso**, o modelo "afirmações com menus suspensos" via Active Screen. Concorda?
3. O que é o formato **INDEX**? Pode enviar uma amostra?
4. `.gotcha` como **ZIP aberto e documentado**, sem criptografia. Aprovado?
5. **Ordem das fases**: A, B, C, D, E, F, G, ou você prioriza outra (por exemplo, Active Screen antes do editor universal)?
6. Para Lab `real`: confirmo que o GOTCHA **só guarda instruções** e nunca executa nem se conecta a infraestrutura de terceiros?

## 17. Validação de alternativas e decisões aprovadas

Você aprovou as seis decisões da seção 16 e pediu que eu conferisse se existe solução mais adequada antes de implementar. Conclusão por item (padrões citados vêm do meu conhecimento; **não os reverifiquei nesta sessão**, só o que está marcado como testado):

| Tema | Alternativa avaliada | Decisão |
| --- | --- | --- |
| Formato de troca de questões | **IMS QTI 3.0** (padrão de avaliações; tem interações de escolha, ordenação, associação, hotspot, "graphic gap match" e estímulo compartilhado, que correspondem aos nossos tipos) | **Manter o `.gotcha` como formato nativo** (Active Screen e Lab não existem em QTI) e **acrescentar QTI 3.0 como adaptador de importação e exportação** no Release 2, para interoperar com Moodle e outros. Registrado no TODO |
| Contêiner do pacote | Arquivo SQLite único (como o Anki) | **ZIP + JSON**: legível, comparável e extraível sem ferramenta. O Anki usa ZIP com banco e mídia por hash, o que confirma a abordagem de mídia por hash |
| Linguagem de condições do Active Screen | Inventar uma sintaxe própria × **JSON Logic** (formato JSON declarativo e sem código executável) | **Adotar a sintaxe do JSON Logic** (`{"and": [{"==": [{"var": "ip"}, "10.0.0.5"]}]}`) com um **avaliador próprio mínimo e em lista fechada**, sem dependência externa. Ganha-se um formato conhecido e portável sem confiar em biblioteca de terceiros para entrada não confiável |
| Máquina de estados das telas | XState (MIT) | **Não adotar**: o motor próprio é pequeno (telas, ações, condições) e precisa rodar **igual** no Python e no navegador. Garanto a paridade com vetores de teste compartilhados |
| Arrastar e soltar | Implementação própria × **`@dnd-kit`** (MIT, gratuito, com sensores de teclado e toque) | **Adotar `@dnd-kit`**: acessibilidade e toque prontos reduzem risco e esforço. Corrige a minha proposta anterior de fazer tudo à mão |
| Sanitização de SVG | `nh3` (sanitizador de HTML) | **Não usar `nh3` para SVG**: usar `lxml` com lista de elementos e atributos permitidos, e exibir SVG **só por `<img>`** (scripts não executam nesse contexto) mais CSP restritiva |
| Dimensões e validação de imagem | Biblioteca mínima só para tamanho (`imagesize`) × **Pillow** | **Pillow**: além de dimensões, verifica decodificação e aplica o limite contra *decompression bomb* |
| Tipos TS a partir do backend | Manter dois modelos à mão | **Gerar JSON Schema do Pydantic e os tipos TS no build**, para não divergirem |
| Editor de regiões | Biblioteca de canvas (Konva, Fabric) | **SVG com eventos de ponteiro, sem biblioteca**: são poucas formas e o ganho de uma dependência não compensa |

### Formato "INDEX"

Confirmado como **HTML salvo de sites de questões**. Já é coberto pelo importador de HTML (inclusive o arquivo `index.html` de uma página salva). O arquivo recebido é idêntico à página 1 já analisada e as imagens continuam relativas a uma pasta que não veio: para importá-las, envie a página **com a pasta de recursos em ZIP**. Para outros sites, o importador passa a ter **adaptadores por estrutura** (hoje: ExamTopics), cada um com seus testes.

### Decisões aprovadas

1. `self_assessed` como tipo de transição: **sim**.
2. Hot Area em dois modos (região clicável e menus suspensos via Active Screen): **sim**.
3. INDEX = HTML de sites de questões: **definido acima**.
4. `.gotcha` como ZIP aberto e documentado: **sim**.
5. Ordem das fases A a G: **sim**.
6. Lab `real` só guarda instruções: **sim**.

## 18. Estado da implementação

Implementado e verificado (280 testes no backend, 29 na interface, `ruff` e `mypy --strict` limpos, e um teste ponta a ponta no navegador com todos os tipos).

### O que existe

| Fase | Entrega | Onde |
| --- | --- | --- |
| A | Modelo canônico v2 com união discriminada por `type`; registro de tipos; fingerprint de conteúdo; migração do modelo v1 e leitura de bancos antigos | `src/gotcha/qtypes/`, `qtypes/migrate.py` |
| A | Recursos por SHA-256 com tipo detectado pelo conteúdo, dimensões (Pillow), limites de tamanho e de pixels, SVG sanitizado (lxml) e original preservado; contagem de referências e lista de órfãos | `qtypes/assets.py`, `storage/library.py` |
| A | Pacote `.gotcha` (ZIP): manifesto com SHA-256 de cada arquivo, reconhecimento por conteúdo, limites contra ZIP malicioso, recusa de arquivo fora do manifesto, recurso ausente marcado como anexo ausente | `qtypes/package.py` |
| B | Múltipla escolha e seleção (com crédito parcial), Build List, Drag and Drop, Hot Area (retângulo, círculo e polígono em coordenadas normalizadas), com corretor, validador, renderizador e editor | `qtypes/*.py`, `web/src/components/renderers`, `components/editor` |
| B | Editor de regiões sobre a imagem (desenhar, mover, ajustar números, marcar corretas) | `components/editor/RegionEditor.tsx` |
| C | Case Study como entidade com seções, guardado uma vez e editável em um lugar | `qtypes/case.py`, `pages/CasePage.tsx` |
| D | Editor universal: blocos (texto, imagem, tabela, código, anexo) com reposicionar, substituir, remover, alt, largura, alinhamento e legenda; prévia vinda do servidor; conversão entre tipos; criação de questão | `pages/EditorPage.tsx`, `qtypes/templates.py` |
| E | Imagens do PDF: extração sem perda (PNG), posição na página, associação à questão por ordem de leitura (antes de `Explanation` é do enunciado, depois é a resposta), filtro de imagens decorativas e aviso do que ficou sem dono ou não pôde ser extraído | `importers/pdf_images.py` |
| F | Active Screen: motor declarativo (componentes de lista fechada, estado, ações, condições JSON Logic), correção por reexecução no servidor e construtor por formulários | `qtypes/screen.py`, `qtypes/logic.py`, `web/src/lib/screen.ts` |
| G | Lab nos três modos, sempre rotulados; o simulado reaproveita o motor do Active Screen; pontuação separada | `qtypes/interactive.py`, `renderers/lab.tsx` |

### Desvios do desenho (e por quê)

- Os campos de cada tipo ficam **no próprio objeto da questão**, e não em um `payload` aninhado. A união discriminada do Pydantic fica mais simples e o JSON Schema sai direto.
- A propriedade `key` do envelope virou `position`, porque o Drag and Drop tem um campo `key` (o gabarito).
- **Questões em branco contam 0 ponto** no percentual (antes eram ignoradas).
- O resultado separa **três** pontuações: automática, autoavaliada e laboratório simulado.
- O servidor também serve `POST /api/preview` (validação e prévia sem salvar), `GET /api/templates/{tipo}` e `POST /api/convert/{tipo}`, para que as regras de validade existam em um só lugar.

### Paridade entre servidor e navegador

O motor do Active Screen e as condições existem em Python e em TypeScript. Os dois passam nos **mesmos vetores de teste** (`tests/vectors/screen.json`). A geometria do Hot Area também é testada nos dois lados com os mesmos casos.

### Critérios de aceitação (seção 13) e o que os cobre

| # | Critério | Verificação |
| --- | --- | --- |
| 1 | Várias imagens por questão | `test_store`, `test_package` (prompt com imagem compartilhada e imagens em opções) |
| 2 | Imagem compartilhada | `test_package`: 9 questões, 1 recurso, 9 referências |
| 3 | Imagens preservadas na exportação | `test_package`: mesmos bytes originais |
| 4 | `.gotcha` sem arquivos externos | `test_package_is_self_contained`, recusa de URL externa |
| 5 | Hot Area após reimportação | `test_package`: mesma geometria e mesma correção |
| 6 | Drag and Drop após reimportação | idem |
| 7 | Build List preserva a sequência | idem |
| 8 | Active Screen preserva estados e interações | idem e vetores compartilhados |
| 9 | Case Study preserva o contexto | `test_case_study_context_is_stored_once_and_referenced` |
| 10 | Lab distingue simulação de execução real | modo obrigatório, faixa fixa na tela, grupos de pontuação separados |
| 11 | Edição manual de todos os tipos | editores por tipo; ida e volta pela API (`test_api`) e teste no navegador |
| 12 | Reimportação não duplica | `test_reimport_does_not_duplicate...` e o teste no navegador (0 adicionadas, 30 ignoradas, 0 órfãos) |
| 13 | Relatório do que não foi preservado | `conversion` por questão, recurso ausente vira anexo ausente com aviso |

### O que ainda não está pronto

- **Gráficos vetoriais do PDF** (tabelas e diagramas desenhados, que não são imagens embutidas) ainda não são capturados; só as imagens embutidas são extraídas. A captura por recorte renderizado continua prevista.
- Alvos do **Drag and Drop sobre uma imagem de fundo**: o modelo e o validador suportam, mas a interface de prova e o editor ainda não posicionam os alvos sobre a imagem.
- **Galeria de mídia** no editor (lista de todos os recursos usados, ausentes e órfãos): a API de órfãos existe, a tela não.
- **Feedback configurável** do Build List e `min_items` do Drag and Drop não entram na correção.
- **Importação de HTML de outros sites**: hoje só a estrutura do ExamTopics (adaptadores por site continuam no plano).
- **Adaptador QTI 3.0** (Release 2).
- O construtor do Active Screen **não importa interfaces originais**, só constrói telas novas; o componente `image` não tem seletor de imagem no editor.
- Atalhos de teclado e leitor de tela foram considerados nos renderizadores (regiões focáveis, alternativas, arrastar com teclado via `@dnd-kit`), mas **não passaram por auditoria de acessibilidade**.

### Resultado da extração de imagens do PDF (medido no PDF AZ-140)

- 341 questões; as **125 interativas ganharam a imagem de resposta** (nenhuma ficou sem).
- 415 imagens de conteúdo extraídas (≈ 20 MB), 376 no enunciado e 126 como resposta.
- 1 523 imagens decorativas (repetidas em quase todas as páginas) ignoradas e informadas no aviso do lote.
- Nenhuma imagem de conteúdo sem questão associada. Importação em ≈ 12 s.
- Fica a ressalva de que é **um** PDF, de um único gerador; PDFs de outros geradores podem associar imagens de forma diferente.
