# Requisitos de interface

Fonte: quatro capturas de tela do VCE Player (Avanset) fornecidas pelo usuário como **referência de funcionalidade**. O GOTCHA terá interface própria: **não copiar logotipo, nome, cores de marca nem arte da Avanset.**

Cada requisito abaixo vira caso de teste antes de ser implementado (ver `PLAN.md`, seção 5). Prioridade: **A** MVP · **B** Release 2.

## 1. Tela de prova

| # | Requisito (observado nas capturas) | Prio. | Critério de aceitação (resumo) |
| --- | --- | --- | --- |
| P1 | Indicador "Questão N de M" (por prova, ex.: "Exam A, Q53") | A | Mostra posição correta ao navegar |
| P2 | **Marcar** a questão para revisão (checkbox `Mark`) | A | Marca persiste ao trocar de questão e ao retomar a sessão |
| P3 | **Anterior / Próxima** | A | Navega sem perder respostas |
| P4 | **Revisar** (menu com opções, ex.: todas, marcadas, não respondidas) | A | Filtra por marcadas e não respondidas |
| P5 | **Mostrar resposta** (modo estudo) | A | Visível só no modo estudo; ausente da interface no modo prova |
| P6 | **Mostrar lista** de questões com estado | A | Lista respondidas, marcadas e em branco, com salto direto |
| P7 | **Salvar sessão** e retomar depois | A | Fechar e reabrir restaura respostas, marcas e tempo restante |
| P8 | **Encerrar prova** com confirmação | A | Calcula resultado no backend e bloqueia edição |
| P9 | Questão de múltipla escolha (uma resposta) | A | Seleção exclusiva; correção correta |
| P10 | Questão de múltipla resposta com **quantidade exata** (ex.: "Select THREE") | A | Valida a quantidade; correção por conjunto exato |
| P11 | Enunciado com **tabela** e texto formatado | A | HTML sanitizado renderiza tabela; scripts são removidos |
| P12 | Alternativas com **código** em fonte monoespaçada e quebras de linha | A | Preserva espaços e indentação |
| P13 | Botão **Exhibit** que abre imagem/diagrama da questão | A | Abre o anexo certo; funciona offline |
| P14 | Zoom (+/−) no exhibit | B | Amplia e reduz a imagem |
| P15 | Link **Instruções** na prova | B | Abre as instruções do perfil do exame |
| P16 | Cronômetro e tempo restante (perfil de exame) | A | Backend é a fonte do tempo; encerra ao zerar |

## 2. Biblioteca de exames

| # | Requisito | Prio. | Critério de aceitação (resumo) |
| --- | --- | --- | --- |
| B1 | Lista de exames importados | A | Lista nome e quantidade de questões |
| B2 | **Adicionar** exame (importar um ou vários arquivos) | A | Cada arquivo gera um lote separado para revisão |
| B3 | **Renomear** | A | Nome persiste |
| B4 | **Remover** com confirmação | A | Remove exame e histórico associados |
| B5 | **Propriedades** (origem, formato, questões, tipos) | A | Mostra metadados corretos |
| B6 | **Histórico** de tentativas | A | Lista data, modo, nota e duração |
| B7 | Um arquivo com várias provas ("Exam A", "Exam B") | A | Importa e permite escolher a prova |
| B8 | Iniciar (`Start`) escolhendo modo e quantidade/tempo | A | Cria sessão no modo escolhido |

## 3. O que as capturas sugerem e fica fora do MVP

- Tipos de questão não pontuados por enquanto (arrastar-e-soltar, hot area, Sim/Não, estudo de caso): viram cartão de referência (ver `PLAN.md`).
- Aviso "UPGRADE NOW" e a frase motivacional da versão gratuita: não aplicável.
- Atualizações do app, janelas redimensionáveis e outros controles de janela: não aplicável a um app web local.

## 4. Questões de design a decidir

1. Estilo de revisão: o menu `Revisar` do VCE abre um menu suspenso; uma tela de lista dedicada pode ser mais simples de testar.
2. Em modo prova, "Mostrar resposta" some ou fica desabilitado? Recomendação: some, para o gabarito não chegar à interface.
3. Tempo restante deve pausar ao salvar a sessão? Recomendação: sim, com pausa explícita registrada.
