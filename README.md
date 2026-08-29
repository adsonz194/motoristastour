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

Os dados são salvos em `data/database.json`, criado automaticamente na primeira execução. A pasta de dados não é versionada para impedir que acessos e dados operacionais sejam enviados ao GitHub.

## Publicação no Render

O arquivo `render.yaml` já está configurado para criar um Web Service Python com Gunicorn e um disco persistente para o banco local. No Render, selecione **New → Blueprint** e conecte este repositório. O serviço usará:

- Build: `pip install -r requirements.txt`
- Start: `gunicorn --workers 1 --bind 0.0.0.0:$PORT app:app`
- Disco persistente: `/opt/render/project/src/data`

O disco exige um plano compatível com armazenamento persistente e a aplicação está fixada em uma única instância, pois o banco JSON é local ao serviço. Para escalar para múltiplas instâncias, migre o armazenamento para PostgreSQL.

## Perfis

- **Administrador:** cria, edita, desativa e exclui usuários, motoristas e consultores; também executa todos os processos.
- **Motorista:** executa os processos operacionais, sem acesso à gestão de usuários.
- **Hostess:** visualiza somente os totais de tours e de grupos Self Gean.
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
- Cada motorista registra individualmente, ao chegar à Casa, se deixou o grupo e voltou ao Prestige ou se permaneceu aguardando. Enquanto houver motorista aguardando, o grupo fica na Casa; quando todos retornam, entra na fila de busca.
- Ao buscar um grupo na Casa, motoristas adicionais podem ser alocados ao mesmo grupo, ficando todos classificados como “Em tour” em conjunto.
- Ao entregar o grupo na Galeria, motorista e carrinho voltam para a disponibilidade do Prestige.
- Galeria controla presença, apresentação e fila de destino, sem registrar a venda.
- A operação é zerada automaticamente ao mudar o dia em America/Sao_Paulo; administradores também podem zerá-la manualmente. Check-ins, cadastros e usuários são tratados corretamente para o novo dia.
- Todo Motorista e Hostess inicia o dia como “Folga ou atestado” e confirma “Fazer check-in” ao entrar, vendo o local definido pelo administrador. Um motorista vinculado não pode ser alocado em um tour antes do check-in; ao confirmar presença, seu cadastro fica disponível quando não houver tour ativo.
- Administradores podem criar, editar, desativar e excluir usuários, motoristas e consultores. A própria conta e o último administrador são protegidos contra perda de acesso; motoristas em tour ativo precisam ser liberados antes de excluir ou mudar a disponibilidade.
- Toda transição gera histórico com data, responsável, estado anterior e novo estado.
