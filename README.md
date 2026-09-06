# Iberostar The Club

Painel operacional para controlar grupos e famílias entre Prestige, Casa, Galeria e destino final. A aplicação de produção é executada em **Python com Flask e Gunicorn**, pronta para publicação no Render.

## Executar localmente

Requer Python 3.11 ou superior.

```bash
python -m venv .venv
./.venv/Scripts/python -m pip install -r requirements.txt
./.venv/Scripts/python app.py
```

No macOS ou Linux, ative o ambiente virtual antes de executar os dois últimos comandos. Abra `http://localhost:4174`.

Em desenvolvimento, sem `DATABASE_URL`, os dados são salvos em `data/database.json`. Em produção, configure `DATABASE_URL` para usar PostgreSQL; o sistema cria automaticamente as tabelas `tour_control_state`, `tour_control_schema` e `tour_control_driver_locations`. As posições dos motoristas ficam separadas do restante do estado operacional para permitir atualizações frequentes sem regravar todo o painel.

## Publicação no Render

O arquivo `render.yaml` já está configurado para criar um Web Service Python gratuito com Gunicorn e PostgreSQL externo. No Render, selecione **New → Blueprint** e conecte este repositório. O serviço usará:

- Build: `pip install -r requirements.txt`
- Start: `gunicorn --workers 1 --bind 0.0.0.0:$PORT app:app`
- Variável obrigatória: `DATABASE_URL` — cole a URL de conexão do Neon como segredo do Render
- Variáveis de Web Push: `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY` e `VAPID_SUBJECT` — configure-as como segredos do Render para ativar as notificações em segundo plano

Gere o par de chaves VAPID uma única vez, no computador de administração, depois de instalar as dependências:

```bash
python generate_vapid_keys.py
```

Copie cada linha gerada para a variável correspondente no Render. Use um e-mail ou endereço válido no `VAPID_SUBJECT`, por exemplo `mailto:operacao@seu-dominio.com`. A `VAPID_PRIVATE_KEY` é secreta: nunca a coloque no GitHub, no código-fonte ou em uma captura de tela. Guarde o mesmo par de chaves; trocar as chaves invalida as assinaturas de notificação já feitas nos aparelhos.

O Render não precisa de disco persistente: cada alteração é gravada no PostgreSQL do Neon. Mantenha uma instância do serviço enquanto a maior parte do estado operacional usar um único registro; as localizações já usam tabela própria, e as demais entidades podem ser normalizadas no futuro caso seja necessário escalar para várias instâncias.

## Notificações no celular e computador

Após configurar as três variáveis VAPID no Render, entre no painel e toque no sino no topo. Ele pede a permissão do navegador, registra uma assinatura exclusiva daquele dispositivo e envia uma notificação de teste. A assinatura permite que o servidor envie avisos mesmo com o navegador fechado, com os totais de tours, Self Gen e convidados Waves → Praia do Forte quando esses dados forem alterados. Os motoristas também recebem um chamado quando a Hostess solicita um carro ou um consultor solicita apoio, além de um segundo aviso quando outro motorista assume o pedido.

Para testar, toque novamente no sino: ele envia outro aviso de teste para o aparelho atual. A permissão e a assinatura são individuais por navegador/aparelho, podem ser retiradas nas configurações do navegador e são removidas do sistema ao sair da conta. Cada perfil recebe somente os totais aos quais já tem acesso no sistema.

No iPhone e iPad com iOS/iPadOS 16.4 ou mais recente, abra o menu Compartilhar do Safari e use **Adicionar à Tela de Início** antes de ativar o sino: Web Push no iOS funciona para o app instalado na Tela de Início. Em Android e computadores, use um navegador com suporte a notificações e permita os avisos do site.

## Localização dos motoristas no mapa

Somente com um check-in ativo, o motorista pode tocar em **Compartilhar minha localização** no próprio celular. O compartilhamento funciona estritamente antes das **15:00 no horário de Salvador/Bahia**; às 15:00, novos inícios e atualizações são bloqueados e os pontos existentes deixam de ser exibidos e são removidos. O navegador pede autorização para usar o GPS e, enquanto o painel permanecer aberto, envia somente a posição mais recente. O sistema não cria histórico de percurso. O motorista também pode parar manualmente; sair da conta e zerar a operação removem a posição.

Para uma validação operacional fora desse horário, uma conta com a permissão **Gerenciar configurações** escolhe um único motorista e ativa em **Configurações** um modo de teste temporário por 30 minutos. A lista exibe todos os usuários Motorista ativos; contas sem vínculo operacional, com cadastro inativo ou sem a permissão de localização continuam visíveis com o motivo do bloqueio. Antes das 15:00, todos continuam seguindo a janela normal; depois das 15:00, somente o motorista selecionado recebe a extensão. Check-in, vínculo de motorista, permissões e isolamento do pedido do consultor continuam obrigatórios. O modo expira sozinho, pode ser encerrado antes e é removido ao zerar ou virar a operação; ao trocar o motorista selecionado fora do horário, o compartilhamento anterior é encerrado e deve ser iniciado novamente.

O mapa global das posições compartilhadas aparece somente no Painel Geral de uma **Hostess autenticada** que tenha a permissão **Ver localização dos motoristas**. Administradores e motoristas não recebem esse mapa, mesmo que um cadastro antigo contenha a permissão. A posição exata fica em uma rota autenticada separada e não entra no carregamento geral do sistema. Antes das 15:00, pontos sem atualização são marcados como desatualizados e, depois do prazo de expiração, deixam de aparecer automaticamente.

A geolocalização do navegador requer HTTPS em produção (ou `localhost` no desenvolvimento). Os mini mapas usam Leaflet com o **OpenStreetMap como fundo**, sempre com a atribuição visível. Para uma operação de grande volume, avalie um provedor de mapas com capacidade e contrato próprios. Em navegadores móveis, o GPS pode ser suspenso quando a tela é bloqueada ou o app é fechado; rastreamento contínuo em segundo plano exigiria um aplicativo móvel dedicado.

## Painel público dos consultores

Abra `https://seu-endereco-no-render.onrender.com/consultores` sem usuário nem senha. A visão geral mostra somente nomes e estados genéricos dos motoristas; ela não recebe coordenadas nem rótulos de local, e não revela pedidos de outras pessoas.

Para pedir apoio, o consultor seleciona o próprio nome e envia a solicitação. O navegador recebe uma credencial temporária e exclusiva daquele pedido, guardada apenas na sessão da aba. Antes de um motorista assumir, nenhuma localização é exibida. Depois do aceite, aquela aba acompanha no mini mapa somente o motorista vinculado ao pedido; a credencial não permite consultar outro pedido ou qualquer outro ponto do mapa global. Ao encerrar o pedido, perder o ponto atual ou chegar às 15:00 em Salvador/Bahia, a localização deixa de ser disponibilizada. Fora desse horário, ela só continua quando o motorista do próprio pedido é o selecionado para o teste temporário. O fundo do mini mapa é o OpenStreetMap.

Como essa página não pede login, a identificação pelo nome é autodeclarada. O fluxo serve para testes e ambientes operacionais controlados; antes de divulgar o endereço livremente na internet, adicione um PIN ou login individual para impedir pedidos feitos em nome de outro consultor.

## Perfis

- **Permissões por usuário:** em **Configurações → Usuários → Novo usuário** (ou **Editar**), o administrador escolhe o perfil como sugestão inicial e marca exatamente as permissões daquela conta. O perfil não obriga acessos extras.
- **Ver Painel Geral:** quando esta for a única permissão marcada, a conta abre somente o Painel Geral em modo leitura. Ela não vê cadastros/configurações e não recebe botões de check-in, criação, alteração de rota, solicitação de carro ou qualquer outra ação operacional.
- O servidor valida cada ação pela permissão recebida; ocultar um botão no navegador não é a única proteção. Uma conta com acesso somente de leitura também recebe apenas os dados necessários para visualizar o painel.
- **Administrador:** cria, edita, desativa e exclui usuários, motoristas e consultores; também executa os processos administrativos e operacionais, mas não recebe o mapa global de GPS reservado à Hostess.
- **Motorista:** visualiza o Painel Geral e acessa somente as etapas operacionais de motorista (Prestige, tour, Casa, Galeria, destino, consulta de motoristas e **Apoio**), sem acesso a cadastros, relatórios, configurações ou ao mapa global. Depois do check-in, pode decidir se compartilha a própria localização antes das 15:00 no horário de Salvador. Convites Waves ficam somente para visualização no painel.
- **Hostess:** vê somente o Painel Geral em modo de leitura, incluindo o mini mapa das posições compartilhadas; pode registrar as quantidades de tours e Self Gen por Ola e solicitar um carro, sem informar hotel, destino ou motorista. Esses totais continuam sendo registrados mesmo em período de fechamento.
- **Concierge:** acessa somente os próprios convites Waves, registra famílias/casais convidados e suas quantidades de pessoas, e marca desistências antes do traslado; não acessa nenhuma função de motorista. Quando houver hotel fechado, o percurso Waves e esse painel ficam indisponíveis automaticamente.

O primeiro acesso administrativo usa o usuário e a senha definidos pela operação. A senha é armazenada somente como hash no banco local.

## Regras operacionais atendidas

- Cada carrinho leva até 5 passageiros além do motorista. Ao selecionar um motorista, o sistema reserva automaticamente um carrinho disponível; não é necessário informar hóspedes nem escolher o carrinho.
- Um tour pode ter mais de um carrinho e motorista, sem duplicar o atendimento. Para adicionar um carrinho, informe somente o motorista.
- A Hostess registra separadamente a quantidade de tours e a quantidade de Self Gen, além da Ola. Por exemplo: 3 tours e 2 Self Gen geram 5 registros. Nesse registro inicial, não há campos de família, casal, consultor ou quantidade de hóspedes. Enquanto os lançamentos ainda aguardam motorista, a Hostess pode selecionar um ou vários para trocar de Ola ou excluir quantidades lançadas a mais; tours já iniciados ficam protegidos contra essas correções.
- Ao iniciar um tour registrado por quantidade, o motorista seleciona o consultor em uma lista de consultores cadastrados e ativos, além dos motoristas que participarão. O painel mostra a dupla de forma direta, por exemplo: **Tour 1 · Rhayane com Paulo**. O nome selecionado fica registrado no tour, mesmo que o cadastro do consultor seja alterado depois.
- Tours são organizados por 1ª Ola (09:00) e 2ª Ola (11:00), sem horário obrigatório de encerramento.
- Antes da saída, o Administrador ou Motorista pode usar **Desistência**. O registro sai das quantidades ativas e das notificações de Tours/Self Gen, mas permanece no Histórico e não pode mais ser iniciado.
- Convites feitos por concierges fazem o trajeto Waves Bahia → Praia do Forte às 07:50 (1ª Ola) ou 09:50 (2ª Ola).
- Em **Configurações → Hotéis e Prestige de saída**, o administrador escolhe o Prestige padrão de saída e cadastra um período de fechamento. Ao fechar um dos hotéis, os tours continuam normalmente pelo outro Prestige configurado: Waves Bahia fechado transfere a saída para o Prestige Selection; Prestige Praia fechado transfere a saída para o Prestige Bahia. Em qualquer fechamento, não há percurso Waves e o painel do Concierge fica indisponível. A Hostess continua registrando as quantidades de tours e Self Gen, e a solicitação de carro continua disponível. Os tours só ficam suspensos se ambos os hotéis estiverem fechados ao mesmo tempo.
- Cada Concierge vê apenas seus próprios convites. O painel exibe o total de famílias convidadas, pessoas convidadas e desistências; uma desistência só pode ser registrada antes do início do traslado.
- Iniciar tour soma uma saída para cada motorista alocado no Prestige.
- Buscar na Casa não cria nova saída de tour.
- Cada motorista registra individualmente, ao chegar à Casa, se deixou o grupo e voltou ao Prestige ou se permaneceu aguardando. O painel mostra os nomes de quem permaneceu e de quem retornou. Enquanto houver motorista aguardando, o grupo fica na Casa; quando todos retornam, entra na fila de busca.
- Em “Registrar Casa”, cada motorista informa apenas se permaneceu com o casal ou se deixou o grupo e retornou ao Prestige. Ao chamar o motorista que falta para a Casa, a lista prioriza quem já saiu com o mesmo grupo e retornou ao Prestige, por estar mais próximo.
- Se o tour precisou de dois ou mais carrinhos e algum motorista retornou ao Prestige, quem permaneceu na Casa não pode seguir sozinho à Galeria. O sistema exige a chegada dos motoristas que faltam para completar os carrinhos necessários.
- Quando a equipe que está com um casal na Casa precisar atender outra família, use **Trocar motoristas**. O casal entra na fila da Casa e o sistema exige a mesma quantidade de carrinhos original na nova busca; assim, por exemplo, dois novos motoristas precisam ser escolhidos para um casal que saiu com dois carrinhos.
- Ao buscar um grupo na Casa, motoristas adicionais podem ser alocados ao mesmo grupo, ficando todos classificados como “Em tour” em conjunto.
- Se o consultor ou grupo seguir diretamente para a Galeria, sem parar na Casa, use **Chegou direto à Galeria** enquanto o tour ainda estiver em percurso. O grupo entra em “Aguardando destino” e os motoristas e carrinhos são liberados normalmente.
- Se **Seguir para Galeria** for marcado por engano e a equipe ainda estiver na Casa, use **Corrigir: ainda estou na Casa** antes de entregar o grupo na Galeria. A correção devolve com segurança o tour, os motoristas e os carrinhos para a Casa, sem apagar ou afetar outro tour.
- Ao entregar o grupo na Galeria, motorista e carrinho voltam para a disponibilidade do Prestige.
- Ao chegar à Galeria, o grupo entra diretamente em “Aguardando destino”; não há etapa de apresentação. Os únicos destinos finais são Lobby Bahia, Lobby Selection, Prestige Praia e Prestige Bahia. Enquanto o grupo estiver a caminho do destino final, use **Alterar destino** para corrigir o local escolhido sem trocar motoristas, carrinhos ou o status do tour. Após confirmar a chegada ao destino, o tour é encerrado.
- A operação é zerada automaticamente somente ao mudar o dia em America/Sao_Paulo; um novo deploy do Render não apaga os dados armazenados no PostgreSQL. Administradores também podem zerá-la manualmente. Check-ins, cadastros e usuários são tratados corretamente para o novo dia.
- Todo Motorista e Hostess inicia o dia como “Folga ou atestado” e confirma “Fazer check-in” ao entrar, vendo o local definido pelo administrador. Um motorista sem check-in não aparece como disponível e não pode ser alocado; ao confirmar presença, seu cadastro fica disponível quando não houver tour ativo.
- A localização exata só é compartilhada após uma ação do próprio motorista e durante um check-in ativo. A janela normal termina às 15:00 no fuso `America/Bahia`; o modo administrativo temporário de 30 minutos exige a escolha de um único motorista e estende somente a janela dele, sem dispensar qualquer outra regra de acesso. Ao fechar a janela efetiva, novos envios são recusados e as posições existentes são removidas. O mapa global é exclusivo da Hostess autenticada; o consultor recebe no máximo o ponto do motorista que assumiu o seu próprio pedido e, fora do horário normal, apenas se ele for o motorista selecionado para o teste, mediante a credencial temporária desse pedido. Não há histórico do trajeto.
- No painel público, o consultor seleciona o próprio cadastro e abre uma solicitação de apoio. Até o aceite, nenhum GPS é mostrado. O motorista livre e com check-in pode assumir o pedido pela fila interna; a partir daí, somente a aba que abriu o chamado acompanha somente aquele motorista. Pedidos encerrados, credenciais incorretas e tentativas de consultar outro pedido nunca retornam uma posição.
- A Hostess pode abrir uma solicitação simples de carro. Os motoristas com check-in, livres e disponíveis recebem o chamado no Painel Geral e assumem uma solicitação; ao aceitar, ficam em **apoio à Hostess** e não podem ser usados em tour, Casa, Galeria ou destino. Quando esse motorista encerra o apoio, a solicitação vinculada é encerrada automaticamente e ele volta a ficar disponível. A Hostess ou o administrador também podem encerrar o próprio pedido antes disso.
- Em **Apoio**, o motorista registra o local obrigatório e, se quiser, uma observação quando estiver ajudando em qualquer outra atividade. Enquanto o apoio estiver aberto, ele aparece como **Em apoio**, não pode ser escolhido para tour nem para outra solicitação de apoio e não parece disponível. O próprio motorista encerra seu apoio; quem tiver a permissão de configurações também pode registrar ou encerrar o apoio de qualquer motorista. Ao encerrar, o motorista volta a ficar disponível somente se tiver feito check-in no dia.
- Ao criar uma conta com perfil Motorista sem selecionar um cadastro existente, o sistema cria e vincula automaticamente o motorista com o mesmo nome. Contas antigas sem vínculo também são corrigidas automaticamente.
- Administradores podem criar, editar, desativar e excluir usuários, motoristas e consultores. A própria conta e o último administrador são protegidos contra perda de acesso; motoristas em tour ativo precisam ser liberados antes de excluir ou mudar a disponibilidade.
- Toda transição gera histórico com data, responsável, estado anterior e novo estado. Qualquer motorista com permissão para operar tours pode assumir, avançar ou corrigir um tour de outro motorista quando for necessário. Alterações de rota e destino ficam destacadas com o nome, conta e perfil de quem executou, além do tour, consultor, rota anterior → nova e motoristas afetados.
