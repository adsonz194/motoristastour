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

- **Administrador:** cria e gerencia usuários e executa todos os processos.
- **Motorista:** executa os processos operacionais, sem acesso à gestão de usuários.
- **Hostess:** visualiza somente os totais de tours e de grupos Self Guide.

O primeiro acesso administrativo usa o usuário e a senha definidos pela operação. A senha é armazenada somente como hash no banco local.

## Regras operacionais atendidas

- Um grupo pode ter mais de um carrinho e motorista, sem duplicar o atendimento.
- Iniciar tour soma uma saída para cada motorista alocado no Prestige.
- Buscar na Casa não cria nova saída de tour.
- Um grupo na Casa pode aguardar transporte enquanto o motorista retorna ao Prestige.
- Galeria controla presença, apresentação e fila de destino, sem registrar a venda.
- Toda transição gera histórico com data, responsável, estado anterior e novo estado.
