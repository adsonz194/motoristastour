# API para aplicativo Android

Base de produção: `https://motoristastour.onrender.com/api/mobile/v1`

Contrato OpenAPI publicado pela própria aplicação: `/api/mobile/v1/openapi.yaml`.

## Fluxo inicial

1. Gere e guarde um UUID por instalação do aplicativo.
2. Envie usuário, senha, `deviceId` e um nome amigável do aparelho para `POST /auth/login`.
3. Guarde o token retornado no armazenamento seguro do Android. Nunca grave o token em logs, analytics ou URLs.
4. Envie `Authorization: Bearer mta_...` em todas as outras requisições.
5. Carregue `GET /bootstrap`. A resposta já vem filtrada pelo perfil e pelas permissões da conta, exatamente como no site.
6. Ao sair, use `POST /auth/logout`. O token é revogado e qualquer posição precisa daquele usuário é removida.

O token dura 30 dias, sobrevive a reinicializações/deploys do servidor e pode ser revogado. Um novo login com o mesmo `deviceId` substitui o token anterior daquela instalação. Cada usuário pode manter até oito instalações ativas.

## Exemplo de login

```http
POST /api/mobile/v1/auth/login HTTP/1.1
Host: motoristastour.onrender.com
Content-Type: application/json

{
  "username": "usuario",
  "password": "senha",
  "deviceId": "97c01d1e-49fe-4f78-b502-a8e8251e13fd",
  "deviceName": "Samsung Galaxy A54"
}
```

Resposta resumida:

```json
{
  "token": "mta_...",
  "tokenType": "Bearer",
  "expiresAt": "2026-10-08T12:00:00+00:00",
  "deviceId": "97c01d1e-49fe-4f78-b502-a8e8251e13fd",
  "apiVersion": "v1",
  "basePath": "/api/mobile/v1",
  "user": {
    "id": "user_...",
    "name": "Nome",
    "role": "MOTORISTA",
    "permissions": ["CHECK_IN"]
  }
}
```

## Retrofit/Kotlin

```kotlin
data class LoginBody(
    val username: String,
    val password: String,
    val deviceId: String,
    val deviceName: String
)

interface TourApi {
    @POST("auth/login")
    suspend fun login(@Body body: LoginBody): MobileSession

    @GET("bootstrap")
    suspend fun bootstrap(@Header("Authorization") bearer: String): BootstrapResponse

    @POST("attendance/check-in")
    suspend fun checkIn(@Header("Authorization") bearer: String): ResponseBody
}
```

Configure o Retrofit com a base terminada em `/`:

```kotlin
Retrofit.Builder()
    .baseUrl("https://motoristastour.onrender.com/api/mobile/v1/")
    .addConverterFactory(MoshiConverterFactory.create())
    .build()
```

## Mesmas funções do painel web

Todas as rotas autenticadas do site possuem um endereço equivalente com o prefixo móvel. Exemplos:

| Função | Rota móvel |
|---|---|
| Sincronizar painel | `GET /bootstrap` |
| Fazer check-in | `POST /attendance/check-in` |
| Registrar tours/Self Gen | `POST /tours/hostess` |
| Corrigir Ola | `PATCH /tours/hostess/selection` |
| Excluir lançamentos | `DELETE /tours/hostess/selection` |
| Executar etapa de tour | `POST /tours/{tourId}/action` |
| Iniciar pedido de Tour já preenchido | `POST /consultant-tour-requests/{requestId}/start` |
| Criar/alterar usuários | `POST /users`, `PUT /users/{userId}` |
| Criar/alterar motoristas | `POST /drivers`, `PUT /drivers/{driverId}` |
| Criar/alterar consultores | `POST /consultants`, `PUT /consultants/{consultantId}` |
| Criar/alterar Self Gen | `POST /self-gens`, `PUT /self-gens/{selfGenId}` |
| Solicitar carro da Hostess | `POST /hostess-requests` |
| Assumir chamado | `POST /drivers/hostess-availability` |
| Acompanhar aproximação | `GET /hostess-requests/{requestId}/approach` |
| Registrar apoio | `POST /driver-supports` |
| Compartilhar GPS do motorista | `POST /drivers/me/location-sharing`, depois `PUT /drivers/me/location` |
| Ver mapa da Hostess | `GET /driver-locations` |
| Configurações operacionais | `/operation/*` e `/hotel-closures/*` |
| Pedido público do Consultor/Self Gen | `/public/consultant-support/options`, `/public/consultant-support-requests/*` |

O servidor não confia no aplicativo para autorização. Cada rota continua validando a permissão, o perfil, o check-in, o estado atual do tour/motorista e a propriedade do chamado.

As rotas `/public/*` não usam o token da conta. O acompanhamento do consultor exige no cabeçalho `X-Support-Access-Token` a credencial devolvida uma única vez na criação daquele pedido.

O pedido público recebe `identityType` (`CONSULTANT` ou `SELF_GEN`), o ID do nome selecionado, `tourId` e `routeStage`. Em Prestige ou Casa, envie também `guestLocation` (`WAVES` ou `SELECTION`). Na saída da Galeria, envie `destinationId`. O servidor liga o nome ao número do Tour e o motorista usa `/consultant-tour-requests/{requestId}/start`, sem redigitar o consultor, o Self Gen ou o destino.

## Localização no Android

O aplicativo deve pedir a permissão de localização ao usuário e enviar latitude, longitude e precisão. Para o motorista:

1. Faça o check-in e leia o `attendance.id` pelo `/bootstrap`.
2. Inicie com `POST /drivers/me/location-sharing` e guarde o `sharingId`.
3. Envie `PUT /drivers/me/location` aproximadamente a cada 15 segundos enquanto o compartilhamento estiver ativo.
4. Encerre com `DELETE /drivers/me/location-sharing`.

A Hostess envia as coordenadas em `POST /hostess-requests` e atualiza `PUT /hostess-requests/{requestId}/location` enquanto o chamado estiver aberto. Depois do aceite, Hostess e motorista designado consultam `GET /hostess-requests/{requestId}/approach`.

As regras atuais continuam obrigatórias: check-in ativo, janela normal até 15:00 no horário de Salvador ou modo temporário de teste para o motorista selecionado, expiração de pontos antigos e remoção ao encerrar o atendimento.

Rastreamento com a tela bloqueada exige um `ForegroundService` Android com notificação visível e as permissões adequadas à versão do Android. A API aceita os pontos, mas o consentimento, a frequência e o ciclo de vida do serviço são responsabilidade do aplicativo.

## Erros e atualização

Erros são JSON no formato `{"error":"mensagem"}`. Trate principalmente:

- `400`: dados inválidos;
- `401`: token ausente, expirado ou revogado — voltar ao login;
- `403`: conta sem permissão;
- `404`: recurso inexistente ou oculto para preservar privacidade;
- `409`: conflito com a regra operacional atual — exibir a mensagem do servidor e sincronizar novamente.

Após qualquer alteração, atualize o estado pelo `/bootstrap`. Para telas em tempo real, use atualização a cada 15 segundos enquanto a tela estiver visível. A API usa JSON UTF-8 e datas ISO 8601 em UTC.

## Notificações nativas

As rotas `/push/*` atuais usam Web Push para o navegador/PWA. Um aplicativo Android nativo deve usar Firebase Cloud Messaging (FCM); o cadastro e envio FCM exigirão as credenciais do projeto Firebase e não devem reutilizar as chaves VAPID do navegador.
