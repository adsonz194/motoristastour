# Self Gen e atualização obrigatória — implantação

## O que muda

- Perfil de usuário `SELF_GEN`, vinculado ao cadastro de um Self Gen ativo, com uma conta por cadastro.
- Tela de solicitações igual à dos consultores: Prestige, busca na Casa e saída da Galeria.
- Duas modalidades: Tour Self Gen ou **Tour normal — apoio a consultor**.
- No apoio, escolha o consultor. O Tour continua normal, preserva o consultor e registra o Self Gen separado como solicitante/apoio.
- Os próximos trechos ficam acessíveis ao Self Gen vinculado e ao consultor do Tour. Outros Self Gen não podem assumir esse vínculo.
- Sem acesso administrativo ou ao painel operacional por esse perfil. A identidade vem do login, não do campo enviado pelo cliente.

No administrador: cadastre o nome em **Consultores → Self Gen**, depois crie/edite um usuário com perfil **Self Gen** e selecione esse cadastro. Não é necessário convertê-lo em Consultor.

## Ordem de publicação

1. Publique estas alterações do servidor/site primeiro. O `mobile-update.json` começa com `versionCode: 0`, sem bloquear ninguém.
2. Aplique as alterações no projeto completo `motoristastourapk` no Windows e use a versão 2.5.0 (código 13), ou um código maior que qualquer APK já distribuído.
3. Execute `.\COMPILAR-APK.bat` na pasta do projeto Android. Ele roda os testes e gera `MotoristasTour-Nativo.apk` e `mobile-update.json` na pasta principal, reutilizando sua chave existente. Não depende de Codemagic nem de Python. Se falhar, não publique arquivos antigos que tenham ficado na pasta.
4. Crie uma Release no GitHub `adsonz194/motoristastourapk`, com a tag indicada no JSON (exemplo `v2.5.0`), e anexe `MotoristasTour-Nativo.apk` **sem mudar seu nome**.
5. Teste o download público e a instalação em um aparelho da equipe. Confira a chave de assinatura e o login. Distribua esta primeira versão com o atualizador antes de exigir atualizações futuras.
6. Só então substitua o `mobile-update.json` deste repositório pelo gerado na sua compilação Windows e publique o servidor. Isso passa a exigir esse código de versão na API.

O servidor lê o JSON em cada solicitação; não busca arquivos arbitrários nem precisa de token do GitHub. O APK deve estar numa Release pública do repositório especificado. Não inclua credenciais ou dados da operação na Release.

## A cada nova versão

1. Aumente `versionCode` em `app/build.gradle.kts` (13 → 14 → 15…) e altere `versionName`.
2. Compile com **a mesma chave**, publique o novo APK na tag correspondente e teste.
3. Atualize o `mobile-update.json` no servidor com o arquivo gerado para esse APK.

Uma alteração de código ou um commit, sozinho, não é uma versão instalável. É necessário compilar e publicar o APK antes de ativar a exigência.

## Comportamento e segurança

- `GET /api/mobile/v1/app-update` é público e sem cache; expõe somente versão, mensagem, URL e SHA-256.
- O app envia `X-App-Version-Code` em cada chamada. O servidor responde HTTP 426 a versões inferiores, inclusive clientes antigos sem o cabeçalho e tokens móveis usando aliases do site.
- O app verifica ao abrir, ao voltar ao primeiro plano e a cada 60 segundos enquanto visível. Uma resposta 426 também aciona o bloqueio.
- A tela não pode ser dispensada. Tem **Baixar atualização**, progresso e **Instalar atualização**. O Android exige autorização/confirmacão do usuário; não há instalação silenciosa.
- O download não recebe o token do login. HTTPS, origem/redirects restritos ao GitHub, limite de tamanho, SHA-256, identificador do pacote, número da versão e assinatura são verificados antes da instalação.
- Falhas de rede/download/instalação não liberam uma versão já bloqueada. Na primeira abertura sem conseguir verificar, é exibida a opção de tentar novamente.
- O site no navegador e o atalho/PWA no iPhone continuam sendo o site: não recebem APK. Este repositório de aplicativo é Android, não contém um projeto iOS nativo.
- Versões anteriores a este atualizador não conseguem ganhar uma tela nova retroativamente: receberão a mensagem de erro da API quando o bloqueio for ativado. A instalação desta primeira versão deve ser manual.

## Assinatura: atenção antes de exigir a atualização

O código anterior assinava até o release com chave de debug local. O `.bat` mantém o uso dessa chave existente; se ela faltar, a compilação para. Também é possível configurar uma chave própria com as variáveis `TOUR_KEYSTORE_PATH`, `TOUR_KEYSTORE_PASSWORD`, `TOUR_KEY_ALIAS` e `TOUR_KEY_PASSWORD` (veja o guia do app). Chaves de máquinas/builds diferentes podem não coincidir. Não foi criada, trocada ou extraída nenhuma chave nesta alteração.

Para atualizar por cima, mantenha `com.motoristastour.nativo` e a mesma chave do APK instalado. Se a chave antiga não estiver disponível, será necessária uma migração manual planejada; não bloqueie a equipe antes disso. Não publique seu keystore no GitHub.

Referência: [requisitos de atualização do Android](https://developer.android.com/google/play/app-updates).

## Recuperação e validação

- Para bloquear temporariamente **somente o APK Android**, use `mobileAppEnabled: false` em `mobile-update.json`. O login e as operações da API móvel retornam `503 MOBILE_APP_DISABLED`, inclusive para sessões móveis já abertas. O site, o navegador no Android e o atalho/PWA no iPhone continuam disponíveis.
- O aviso é definido em `maintenanceMessage`. O endpoint `app-update` informa a manutenção, e o logout continua permitido. Para liberar novamente o APK, altere explicitamente para `mobileAppEnabled: true`, preservando os campos de versão/assinatura. Ao substituir o JSON por uma versão compilada, preserve o bloqueio até a liberação autorizada.

- Para suspender a exigência numa emergência, publique `versionCode: 0` no JSON. Não apague cadastros/dados e não revogue sessões em massa.
- Um JSON inválido retorna 503 no app (não contorna uma exigência já conhecida); o site permanece disponível.
- Não reutilize uma tag/URL para trocar o APK de uma versão já publicada. Use código e tag novos.
- Teste: APK antigo → bloqueio; download → confirmação Android → versão nova → desbloqueio; internet desligada; download incompleto; SHA inválido; assinatura errada; cancelamento do instalador; Self Gen normal/próprio; consulta por outro usuário.

## Comandos locais

```bash
python -m unittest discover -s tests -q
corepack pnpm install --frozen-lockfile
corepack pnpm ui:build
```

O build da interface agora atualiza `static/`, a pasta realmente servida no Render, preservando os bundles antigos. O Render atualmente só executa `pip install`, por isso os arquivos compilados precisam acompanhar o commit.
