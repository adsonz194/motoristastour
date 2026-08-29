# Iberostar Tour Interno

Painel operacional para controlar grupos e familias entre Prestige, Casa, Galeria e destino final. O projeto foi construído a partir do plano operacional e da referência visual fornecidos.

## Executar localmente

```bash
pnpm install
pnpm dev
```

Em outro terminal, execute a API:

```bash
pnpm start
```

Abra `http://localhost:5173`. A API usa a porta `4174` e salva seus dados em `data/database.json`, criado automaticamente na primeira execução.

Para gerar a versão de produção, execute `pnpm build`; em seguida, `pnpm start` publica o conteúdo de `dist/` na porta `4174`.

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
