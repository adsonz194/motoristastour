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

Em desenvolvimento, sem `DATABASE_URL`, os dados são salvos em `data/database.json`. Em produção, configure `DATABASE_URL` para usar PostgreSQL; o sistema cria automaticamente as tabelas `tour_control_state` e `tour_control_schema` e preserva todo o estado operacional no banco.

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

O Render não precisa de disco persistente: cada alteração é gravada no PostgreSQL do Neon. Mantenha uma instância do serviço enquanto o sistema usar o estado operacional em um único registro; para escalar a várias instâncias no futuro, a estrutura pode ser normalizada em tabelas por entidade.

## Notificações no celular e computador

Após configurar as três variáveis VAPID no Render, entre no painel e toque no sino no topo. Ele pede a permissão do navegador, registra uma assinatura exclusiva daquele dispositivo e envia uma notificação de teste. A assinatura permite que o servidor envie avisos mesmo com o navegador fechado, com os totais de tours, Self Gen e convidados Waves → Praia do Forte quando esses dados forem alterados. Os motoristas também recebem um chamado quando a Hostess solicita carro e um segundo aviso quando outro motorista assume esse apoio.

Para testar, toque novamente no sino: ele envia outro aviso de teste para o aparelho atual. A permissão e a assinatura são individuais por navegador/aparelho, podem ser retiradas nas configurações do navegador e são removidas do sistema ao sair da conta. Cada perfil recebe somente os totais aos quais já tem acesso no sistema.

No iPhone e iPad com iOS/iPadOS 16.4 ou mais recente, abra o menu Compartilhar do Safari e use **Adicionar à Tela de Início** antes de ativar o sino: Web Push no iOS funciona para o app instalado na Tela de Início. Em Android e computadores, use um navegador com suporte a notificações e permita os avisos do site.

## Painel público dos consultores

Abra `https://seu-endereco-no-render.onrender.com/consultores` para consultar, sem usuário nem senha, os nomes, status e a localização operacional atual dos motoristas, como **Disponível**, **Na Casa**, **Em tour**, **A caminho da Galeria** ou **Em apoio · local informado**. É uma página de leitura, atualizada a cada 30 segundos, sem dados de hóspedes, tours, usuários ou ações operacionais.

## Perfis

- **Permissões por usuário:** em **Configurações → Usuários → Novo usuário** (ou **Editar**), o administrador escolhe o perfil como sugestão inicial e marca exatamente as permissões daquela conta. O perfil não obriga acessos extras.
- **Ver Painel Geral:** quando esta for a única permissão marcada, a conta abre somente o Painel Geral em modo leitura. Ela não vê cadastros/configurações e não recebe botões de check-in, criação, alteração de rota, solicitação de carro ou qualquer outra ação operacional.
- O servidor valida cada ação pela permissão recebida; ocultar um botão no navegador não é a única proteção. Uma conta com acesso somente de leitura também recebe apenas os dados necessários para visualizar o painel.
- **Administrador:** cria, edita, desativa e exclui usuários, motoristas e consultores; também executa todos os processos.
- **Motorista:** visualiza o Painel Geral e acessa somente as etapas operacionais de motorista (Prestige, tour, Casa, Galeria, destino, consulta de motoristas e **Apoio**), sem acesso a cadastros, relatórios ou configurações. Convites Waves ficam somente para visualização no painel.
- **Hostess:** vê somente o Painel Geral em modo de leitura; pode registrar as quantidades de tours e Self Gen por Ola e solicitar um carro, sem informar hotel, destino ou motorista. Esses totais continuam sendo registrados mesmo em período de fechamento.
- **Concierge:** acessa somente os próprios convites Waves, registra famílias/casais convidados e suas quantidades de pessoas, e marca desistências antes do traslado; não acessa nenhuma função de motorista. Quando houver hotel fechado, o percurso Waves e esse painel ficam indisponíveis automaticamente.

O primeiro acesso administrativo usa o usuário e a senha definidos pela operação. A senha é armazenada somente como hash no banco local.

## Regras operacionais atendidas

- Cada carrinho leva até 5 passageiros além do motorista. Ao selecionar um motorista, o sistema reserva automaticamente um carrinho disponível; não é necessário informar hóspedes nem escolher o carrinho.
- Um tour pode ter mais de um carrinho e motorista, sem duplicar o atendimento. Para adicionar um carrinho, informe somente o motorista.
- A Hostess registra separadamente a quantidade de tours e a quantidade de Self Gen, além da Ola. Por exemplo: 3 tours e 2 Self Gen geram 5 registros. Nesse registro inicial, não há campos de família, casal, consultor ou quantidade de hóspedes.
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
- A Hostess pode abrir uma solicitação simples de carro. Os motoristas com check-in, livres e disponíveis recebem o chamado no Painel Geral e assumem uma solicitação; ao aceitar, ficam em **apoio à Hostess** e não podem ser usados em tour, Casa, Galeria ou destino. Quando esse motorista encerra o apoio, a solicitação vinculada é encerrada automaticamente e ele volta a ficar disponível. A Hostess ou o administrador também podem encerrar o próprio pedido antes disso.
- Em **Apoio**, o motorista registra o local obrigatório e, se quiser, uma observação quando estiver ajudando em qualquer outra atividade. Enquanto o apoio estiver aberto, ele aparece como **Em apoio**, não pode ser escolhido para tour nem para apoio da Hostess e não parece disponível. O próprio motorista encerra seu apoio; quem tiver a permissão de configurações também pode registrar ou encerrar o apoio de qualquer motorista. Ao encerrar, o motorista volta a ficar disponível somente se tiver feito check-in no dia.
- Ao criar uma conta com perfil Motorista sem selecionar um cadastro existente, o sistema cria e vincula automaticamente o motorista com o mesmo nome. Contas antigas sem vínculo também são corrigidas automaticamente.
- Administradores podem criar, editar, desativar e excluir usuários, motoristas e consultores. A própria conta e o último administrador são protegidos contra perda de acesso; motoristas em tour ativo precisam ser liberados antes de excluir ou mudar a disponibilidade.
- Toda transição gera histórico com data, responsável, estado anterior e novo estado. Qualquer motorista com permissão para operar tours pode assumir, avançar ou corrigir um tour de outro motorista quando for necessário. Alterações de rota e destino ficam destacadas com o nome, conta e perfil de quem executou, além do tour, consultor, rota anterior → nova e motoristas afetados.
