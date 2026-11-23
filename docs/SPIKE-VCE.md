# Spike VCE — classificação das amostras

Fase 0 do `PLAN.md`. Escopo desta análise: **classificar** os arquivos `.vce` recebidos, olhando só tamanho, cabeçalho, entropia e texto legível no início. Não houve tentativa de decodificar, descriptografar ou ler o conteúdo das questões, e este documento não reproduz nenhum conteúdo de exame. Os arquivos ficam fora do repositório.

## Amostras analisadas (4)

| Arquivo | Tamanho | Entropia média por bloco de 4 KB | Observação |
| --- | --- | --- | --- |
| Exam1 | 107 283 B | 7,31 | Misto: trechos de baixa entropia e trechos densos |
| Exam2 | 437 733 B | 7,53 | Idem |
| S10-210_formatted | 460 615 B | 7,63 | Idem; muitos trechos de texto ASCII legível |
| Exam3 | 430 B | 5,45 | Pequeno demais para conter um exame; provavelmente vazio, truncado ou apenas cabeçalho |

## Achados

1. **Assinatura comum:** os 4 arquivos começam com `85 A8 03 04`, seguido de bytes variáveis (`00 XX 07 01 02 00`) e de um campo de texto legível que, nos quatro, lê-se `000-800`. Parece um código padrão, não um código de exame real.
2. **Não é contêiner padrão:** nenhuma assinatura de ZIP, SQLite, PDF, gzip/zlib, imagens ou executáveis foi encontrada, nem no início nem embutida.
3. **Conteúdo misto:** a entropia varia de ~2 a ~7,95 bits/byte entre blocos. Há áreas estruturadas ou textuais e áreas densas, compatíveis com **compressão ou criptografia**. Sem tentar decodificar, não dá para distinguir uma da outra.
4. **Campo de título não está em texto puro:** o campo logo após o código aparece transformado. Por exemplo, o do arquivo `S10-210_formatted` lê-se como uma versão deslocada do nome, e não como o nome em si. Isso indica que o formato aplica **alguma camada de ofuscação**, mesmo nos metadados.
5. **Blocos repetidos:** de 0,7% a 11% dos blocos de 16 bytes se repetem (Exam2: 11%). Isso é incomum em dados criptografados com modo forte, mas não conclusivo.

## Classificação provisória

**Resultado (b): somente via PDF exportado pelo aplicativo original.**

Motivos:

- Formato proprietário sem especificação pública e sem leitor aberto conhecido (`docs/VALIDACAO.md`).
- Há ofuscação nos metadados e conteúdo denso que não pode ser lido sem decodificar.
- Ler o conteúdo exigiria **engenharia reversa de uma camada que se comporta como proteção**. Isso contraria a regra 5 do projeto (sem DRM/criptografia) e traz o risco legal descrito em `docs/VALIDACAO.md`. A decisão de ir além é do usuário e depende dos termos da Avanset, ainda não lidos.

## Limites desta análise

- Amostra pequena (3 exames úteis). As variantes de versão (`07 01 02`) e o byte variável após a assinatura não foram interpretados.
- Não foi verificado se o aplicativo original consegue exportar estes arquivos para PDF.
- O arquivo Exam3 (430 B) não permite conclusão.

## Próximos passos

1. Abrir um dos `.vce` no aplicativo original e tentar exportar para PDF (exige a edição que permita exportar; o demo mostra só parte das questões). Isso confirma ou derruba o resultado (b).
2. Obter os PDFs de simulado reais para medir a extração com `pdfplumber` e `pypdfium2`.
3. Ler os termos da Avanset antes de qualquer decisão sobre leitura direta.
4. Transformar as descobertas em casos de teste com fixtures **sintéticas** (por exemplo, "arquivo com assinatura desconhecida e entropia alta é recusado com orientação para exportar PDF").
