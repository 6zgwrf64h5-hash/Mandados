# Mandados do dia: especificação para manutenção

Documento para quem for alterar o aplicativo (Claude Code ou outra pessoa). Descreve o que existe e **o que não pode quebrar**.

## 1. O que é
Aplicativo web instalável (PWA) para um **Oficial de Justiça** da Comarca de **Foz do Iguaçu (TJPR)**, usado no **iPhone**, em campo. Fluxo: ler os mandados em PDF, mandar a mensagem padrão por **WhatsApp**, montar a **rota** do dia, registrar **certidões** e organizar tudo. Interface em **português do Brasil**, pensada para tela de celular (uma mão, botões grandes).

## 2. Arquivos
| Arquivo | Para quê |
|---|---|
| `index.html` | **O aplicativo inteiro** (HTML + CSS + JS, ~500 KB). Dois `<script>`: o 1º é a tabela de ruas (OpenStreetMap, Foz e Santa Terezinha de Itaipu); o 2º é o app. Dentro do 2º há o bloco `/*PURE-START*/ … /*PURE-END*/` com a **lógica pura** (classificação, telefones, rota, certidões), sem DOM. |
| `manifest.webmanifest`, ícones | Instalação na Tela de Início. |
| `sw.js` | Service worker: guarda o app e as bibliotecas (PDF.js, pdf-lib, JSZip) para abrir **sem sinal**. **Troque `VERSAO` a cada mudança** em `index.html`, senão o iPhone pode ficar com a antiga. |

`MODO_ATALHO = true` em `index.html` liga o modo "aplicativo no aparelho": sem cópia na conta do Claude, com **backup em arquivo** e **IA por chave própria**. (A mesma base roda dentro do Claude como artefato com `MODO_ATALHO = false`; aqui isso não importa.)

## 3. Armazenamento
- Estado (mandados, ajustes, modelos, rotas, aprendizado): `localStorage`, chave `mandados-v3`.
- PDFs e prints das certidões: **IndexedDB** `mandados-files`, loja `files` (chave = id do arquivo).
- Backup: arquivo `Backup-Mandados-AAAA-MM-DD.json` com `{app:'mandados-do-dia', versao:1, estado, arquivos:{id:{tipo,b64}}}`. **Não mude esse formato sem manter a leitura dos antigos.**
- O iPhone pode apagar dados do app: por isso existe o **backup em arquivo** e o aviso "Faltam PDFs" (botão *Resolver*: escolher o mesmo PDF de novo).

## 4. Regras de negócio (não quebrar)

### 4.1 Classificação do mandado (cor do cartão)
- **Verde (`enviar`)**: pode mandar mensagem. **Amarelo (`conferir`)**: em dúvida. **Vermelho (`nao_enviar`)**: não mandar. **Roxo**: sem telefone.
- **Vermelho** quando: **1º Juizado** (Cível, Criminal ou da Fazenda; "1ª Vara" **não** é); **citação criminal**; o **ato** é penhora, arresto, sequestro, busca e apreensão, reintegração, imissão, avaliação, **prisão, condução coercitiva, despejo, desocupação**; **medida protetiva com afastamento do lar IMPOSTO** pela decisão.
- **Citação sempre pode ir por mensagem**, inclusive em execução e mesmo que a penhora venha depois ("Citação, penhora e avaliação" = verde; "Penhora e avaliação" = vermelho).
- **Medida protetiva**: só o **afastamento do lar imposto** impede. Distanciamento, proibição de contato/aproximação, prorrogação, afastamento indeferido, "sem afastamento" e "art. 22, II" citado só como lei **não** impedem. Se o texto só cita a lei, fica **amarelo**.
- As exceções são **editáveis** em *Meus dados > Exceções* (lista de regras com texto, condição `''|criminal|medida|citacao` e ação).
- Mandado vermelho **mostra** o botão do WhatsApp (com aviso); ao tocar no número ele passa a "pode enviar". Amarelo não mostra o botão (há "Marcar: pode enviar").
- Na lista, entre os verdes vêm **primeiro os que só se cumprem por WhatsApp** (sem endereço físico ou com endereço em outra comarca).

### 4.2 Telefones
- DDD **45** e o **9** entram sozinhos quando faltam. O mesmo número em formatos diferentes aparece **uma vez**, com nove dígitos. Dois números no mesmo campo são separados.
- **Ignorar** telefones de fórum, vara, CEJUSC, Defensoria, Patrulha Maria da Penha.
- Fixo é marcado "(fixo)" e **também** recebe link (alguns fixos têm WhatsApp). Número com 13 dígitos ou lixo **não** é aceito.
- Cada número tem seu botão. "Documentos em análise" registra uma mensagem especial que **não** conta como envio.

### 4.3 Endereço
- **Local** = Foz do Iguaçu e Santa Terezinha de Itaipu (cidades editáveis). **Fora** = outra comarca. **Eletrônico** = "Intimação por meio eletrônico"/sem endereço físico.
- Endereço enviado ao Maps só com **rua, número e cidade**.

### 4.4 Custas e transporte
- Diligência padrão **R$ 108,63** (editável, por mandado). Transporte **R$ 40,00** por mandado com endereço físico na comarca (editável). Resumo por dia e mês.

### 4.5 Mensagem e fila
- Mensagem padrão com marcadores `{NOME} {OFICIAL} {MATRICULA}…`, editável. Link `https://wa.me/55DDDNÚMERO?text=…`.
- **Enviar em sequência**: uma pessoa por vez, **um passo por número de telefone**, botão grande que abre o WhatsApp; pular, voltar, desfazer; guarda a fila se a página recarregar.
- Mensagem repetida após 24 h; "tentativas" agrupam envios próximos.

### 4.6 Certidões
- Duas partes: **física** (no endereço) e **on-line** (WhatsApp), mais certidão inteira. Modelos próprios com marcadores. Empresa (LTDA etc.) troca o texto ("a empresa NOME").
- **Certidão positiva por WhatsApp**: a frase "CERTIFICO ainda que a identidade foi confirmada previamente." entra **sempre**. Caixinha opcional "Antes, fui ao endereço físico e não encontrei" (só quando há endereço físico) coloca no começo o relato do endereço.
- Certidão negativa leva a diligência. "Editar por IA" (e troca simples sem IA).

### 4.7 Rota
- Rotas de **até 10 paradas** (limite do Google Maps), editável de 3 a 10. Ordem padrão **em linha reta**, bairro por bairro, começando pelos bairros que vêm primeiro (**Portal da Foz, Morumbi**) e terminando perto de um ponto (a casa do usuário, configurável). Modo "na ordem dos meus bairros" (lista editável).
- **Ajuste manual** (posição, ▲▼, arrastar) vale primeiro e vira a **rota oficial** (lista "Por rota" e impressão).
- **Aprendizado** simples: "Salvar esta rota" guarda só rua/bairro/número (sem nomes); com 2+ rotas coerentes passa a ordenar parecido. Pode desligar.
- Paradas marcadas formam rota própria; enviar a rota por **SMS** e **WhatsApp** (números em *Meus dados*, vazios de fábrica).
- Impressão com visualização.

### 4.8 IA (opcional, chave própria)
- Chamadas direto do navegador à API da Anthropic com o cabeçalho `anthropic-dangerous-direct-browser-access: true` e a chave digitada pelo usuário (**guardada só no aparelho**, nunca no código). Usos: ler mandados (texto/foto), classificar, "Certificar por IA", "Editar por IA", resumos.
- **Sempre avisar** que o conteúdo vai para a Anthropic e permitir desligar. Sem chave, tudo que não depende de IA continua funcionando.

## 5. Regras para quem altera
1. **Nunca** coloque dado pessoal no repositório (nome, matrícula, telefone, endereço, PDF, backup). Ele é público.
2. A cada mudança em `index.html`, **troque `VERSAO` em `sw.js`**.
3. Mantenha o visual e os textos. Mudança de regra de negócio só com pedido explícito.
4. Teste em navegador (Playwright) o que for possível: abrir, instalar, offline, backup e restauração, fila de envio, classificação (casos acima). Diga claramente **o que não foi testado no iPhone**.
5. Não leia PDFs reais em testes que serão commitados: use dados inventados.

## 6. Pontos a confirmar no iPhone (não dá para testar no computador)
- Persistência dos dados depois de fechar o app; modo avião; folha de compartilhar do backup; `sms:` abrindo o Mensagens dentro do app instalado; `wa.me` abrindo o WhatsApp; leitura de PDF grande; câmera/foto para "Certidão física (foto)".
