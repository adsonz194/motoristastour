# Iberostar Tour Interno

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

O Render não precisa de disco persistente: cada alteração é gravada no PostgreSQL do Neon. Mantenha uma instância do serviço enquanto o sistema usar o estado operacional em um único registro; para escalar a várias instâncias no futuro, a estrutura pode ser normalizada em tabelas por entidade.

## Notificações no celular e computador

Após entrar no painel, toque no sino no topo para permitir as notificações deste site naquele aparelho. O sistema envia um resumo com a quantidade de tours, Self Gean e convidados do Waves → Praia do Forte sempre que esses totais mudarem enquanto o painel estiver aberto ou em segundo plano; ele consulta as atualizações a cada 30 segundos.

No celular, para uma experiência de aplicativo e notificações nativas, abra o menu do navegador e use **Adicionar à tela inicial**. A permissão é individual por navegador/aparelho e pode ser retirada nas configurações do navegador. Cada perfil recebe apenas os totais aos quais já tem acesso no sistema.

## Painel público dos consultores

Abra `https://seu-endereco-no-render.onrender.com/consultores` para consultar, sem usuário nem senha, somente os nomes e os status atuais dos motoristas. É uma página de leitura, atualizada a cada 30 segundos, sem dados de hóspedes, tours, usuários ou ações operacionais.

## Perfis

- **Administrador:** cria, edita, desativa e exclui usuários, motoristas e consultores; também executa todos os processos.
- **Motorista:** visualiza o Painel Geral e acessa somente as etapas operacionais de motorista (Prestige, tour, Casa, Galeria, destino e consulta de motoristas), sem acesso a cadastros, relatórios ou configurações. Convites Waves ficam somente para visualização no painel.
- **Hostess:** acessa somente a própria tela para registrar as quantidades de tours e Self Gean por onda.
- **Concierge:** acessa somente os próprios convites Waves, registra famílias/casais convidados e suas quantidades de pessoas, e marca desistências antes do traslado.

O primeiro acesso administrativo usa o usuário e a senha definidos pela operação. A senha é armazenada somente como hash no banco local.

## Regras operacionais atendidas

- Cada carrinho leva até 5 passageiros além do motorista. Ao selecionar um motorista, o sistema reserva automaticamente um carrinho disponível; não é necessário informar hóspedes nem escolher o carrinho.
- Um tour pode ter mais de um carrinho e motorista, sem duplicar o atendimento. Para adicionar um carrinho, informe somente o motorista.
- A Hostess registra separadamente a quantidade de tours e a quantidade de Self Gean, além da onda. Por exemplo: 3 tours e 2 Self Gean geram 5 registros. No início da saída, o motorista informa somente os motoristas que participarão; não há campos de família, casal, consultor ou quantidade de hóspedes.
- Tours são organizados por 1ª onda (09:00) e 2ª onda (11:00), sem horário obrigatório de encerramento.
- Convites feitos por concierges fazem o trajeto Waves Bahia → Praia do Forte às 07:50 (1ª onda) ou 09:50 (2ª onda).
- Cada Concierge vê apenas seus próprios convites. O painel exibe o total de famílias convidadas, pessoas convidadas e desistências; uma desistência só pode ser registrada antes do início do traslado.
- Iniciar tour soma uma saída para cada motorista alocado no Prestige.
- Buscar na Casa não cria nova saída de tour.
- Cada motorista registra individualmente, ao chegar à Casa, se deixou o grupo e voltou ao Prestige ou se permaneceu aguardando. O painel mostra os nomes de quem permaneceu e de quem retornou. Enquanto houver motorista aguardando, o grupo fica na Casa; quando todos retornam, entra na fila de busca.
- Em “Registrar Casa”, cada motorista informa apenas se permaneceu com o casal ou se deixou o grupo e retornou ao Prestige. Ao chamar o motorista que falta para a Casa, a lista prioriza quem já saiu com o mesmo grupo e retornou ao Prestige, por estar mais próximo.
- Se o tour precisou de dois ou mais carrinhos e algum motorista retornou ao Prestige, quem permaneceu na Casa não pode seguir sozinho à Galeria. O sistema exige a chegada dos motoristas que faltam para completar os carrinhos necessários.
- Quando a equipe que está com um casal na Casa precisar atender outra família, use **Trocar motoristas**. O casal entra na fila da Casa e o sistema exige a mesma quantidade de carrinhos original na nova busca; assim, por exemplo, dois novos motoristas precisam ser escolhidos para um casal que saiu com dois carrinhos.
- Ao buscar um grupo na Casa, motoristas adicionais podem ser alocados ao mesmo grupo, ficando todos classificados como “Em tour” em conjunto.
- Ao entregar o grupo na Galeria, motorista e carrinho voltam para a disponibilidade do Prestige.
- Ao chegar à Galeria, o grupo entra diretamente em “Aguardando destino”; não há etapa de apresentação. Os únicos destinos finais são Lobby Bahia, Lobby Selection, Prestige Praia e Prestige Selection. Após confirmar a chegada ao destino, o tour é encerrado.
- A operação é zerada automaticamente ao mudar o dia em America/Sao_Paulo; administradores também podem zerá-la manualmente. Check-ins, cadastros e usuários são tratados corretamente para o novo dia.
- Todo Motorista e Hostess inicia o dia como “Folga ou atestado” e confirma “Fazer check-in” ao entrar, vendo o local definido pelo administrador. Um motorista vinculado não pode ser alocado em um tour antes do check-in; ao confirmar presença, seu cadastro fica disponível quando não houver tour ativo.
- Ao criar uma conta com perfil Motorista sem selecionar um cadastro existente, o sistema cria e vincula automaticamente o motorista com o mesmo nome. Contas antigas sem vínculo também são corrigidas automaticamente.
- Administradores podem criar, editar, desativar e excluir usuários, motoristas e consultores. A própria conta e o último administrador são protegidos contra perda de acesso; motoristas em tour ativo precisam ser liberados antes de excluir ou mudar a disponibilidade.
- Toda transição gera histórico com data, responsável, estado anterior e novo estado.
