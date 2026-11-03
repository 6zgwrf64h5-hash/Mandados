# Mandados do dia: atalho para o iPhone

Este pacote é o **aplicativo instalável** (PWA). Depois de instalado ele:
- abre pelo ícone na tela inicial, em tela cheia, como um app;
- guarda a lista, os PDFs e os ajustes **no próprio iPhone**;
- abre **sem sinal** (depois da primeira vez com internet);
- não depende do aplicativo do Claude.

> **Importante:** o repositório do GitHub será **público** (é o que o GitHub grátis exige para hospedar a página). Por isso **nenhum dado seu está no código**: nome, matrícula, telefones e o "termina perto de" são digitados em *Meus dados* e ficam **só no seu aparelho**. **Nunca suba PDFs de mandados nem arquivos de backup para o GitHub.**

---

## Parte 1: Colocar no ar (uma vez só, uns 15 minutos)

### 1. Conta no GitHub
Abra **github.com** no Safari e crie uma conta gratuita (e-mail + senha).

### 2. Criar o repositório
1. Toque em **+** (canto superior) > **New repository**.
2. Nome: `mandados`.
3. Marque **Public**.
4. Toque em **Create repository**.

### 3. Subir os arquivos
1. Neste pacote, abra o `.zip` no app **Arquivos** (toque nele para descompactar).
2. No repositório, toque em **Add file > Upload files**.
3. Escolha **todos os arquivos** da pasta (`index.html`, `manifest.webmanifest`, `sw.js`, os 4 ícones `.png`, `.gitignore`, `LEIA-ME.md`, `ESPECIFICACAO.md`, `PROMPT-CLAUDE-CODE.md`).
4. Toque em **Commit changes**.

> Se o iPhone não deixar escolher vários arquivos, use o computador com Windows (arraste os arquivos para a página) ou, no Safari, toque em **aA > Versão para computador**.

### 4. Ligar a página (GitHub Pages)
1. No repositório: **Settings > Pages**.
2. Em **Build and deployment**, escolha **Deploy from a branch**.
3. Branch: **main** e pasta **/ (root)**. Toque em **Save**.
4. Espere 1 a 2 minutos. O endereço aparece no topo da tela, no formato:
   `https://SEU-USUARIO.github.io/mandados/`

### 5. Instalar no iPhone
1. Abra esse endereço no **Safari** (não dentro de outro aplicativo).
2. Toque em **Compartilhar** (quadrado com seta) > **Adicionar à Tela de Início** > **Adicionar**.
3. **Abra sempre pelo ícone novo.** Abrir pelo Safari ou por link não é a mesma coisa.

---

## Parte 2: Primeiro uso

1. Abra pelo ícone. Aparecem mandados de teste: toque em **Meus dados** e preencha **nome, matrícula, diligência**.
2. Em **Minha rota**: onde termina (sua casa, por exemplo), bairros, paradas por rota.
3. Em **Meus dados**: o **celular do SMS** e o **WhatsApp** que recebem a rota (se quiser).
4. **Para a IA** (opcional), cole a **chave da API da Anthropic** em *Meus dados > IA*. Ela fica só no aparelho. A cobrança é por uso, em conta de desenvolvedor **separada do plano do Claude** (pode ser preciso colocar crédito antes de a chave funcionar). Sem chave, tudo continua funcionando, menos ler foto de mandado, "Certificar por IA" e "Editar por IA".
5. **Primeiro PDF com internet:** adicione um PDF **com sinal**. É nessa hora que o iPhone guarda as ferramentas de leitura de PDF, e depois elas funcionam sem sinal.

### Levar os dados que você tem hoje (opcional)
1. Na página do Claude: **Meus dados > Backup em arquivo > Salvar backup em arquivo**. Guarde no app **Arquivos**.
2. No atalho: na tela inicial, **Restaurar de um arquivo** (ou *Meus dados > Backup em arquivo > Restaurar*). Escolha o arquivo e toque em **Juntar** ou **Substituir tudo**.
   PDFs que já tinham sumido não voltam: escolha os arquivos de novo.

---

## Parte 3: Cuidados do dia a dia

- **Backup em arquivo toda semana.** Toque em **Backup em arquivo** na tela inicial e guarde no app Arquivos (ou iCloud). A linha do topo mostra há quantos dias foi o último. O iPhone **ainda pode apagar** dados se faltar espaço ou se você remover o ícone, e **o backup é o seu seguro**.
- **O arquivo de backup tem dados pessoais** (nomes, endereços, PDFs). Não compartilhe nem suba para o GitHub.
- **Atualizações:** quando mudarmos algo, o arquivo `index.html` é trocado no GitHub. Abra o app com internet e feche e abra de novo: ele pega a versão nova.
- **Teste no seu iPhone na primeira semana** e anote o que não funcionou: eu não consegui testar no aparelho de verdade, só em navegador.

## O que eu preciso que você confira no iPhone
- O ícone aparece e o app abre em tela cheia.
- Fechar o app, abrir de novo e os mandados e PDFs continuarem lá.
- Modo avião: o app abre e mostra os mandados.
- **Backup em arquivo** abre a folha de compartilhar e dá para salvar em Arquivos.
- O botão de **SMS** da rota abre o app Mensagens (aqui deve funcionar, diferente de dentro do Claude).
- O botão do **WhatsApp** abre a conversa com a rota pronta.
