# HelpDesk API

![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%2B-4169E1?logo=postgresql&logoColor=white)
![Tests](https://img.shields.io/badge/tests-11%20passing-2ea44f)

API REST para gerenciamento de chamados de suporte de TI. O projeto foi
construído como uma aplicação de portfólio, com foco em segurança, separação de
responsabilidades, testes automatizados e evolução por migrations.

## Sumário

- [Sobre](#sobre)
- [Funcionalidades](#funcionalidades)
- [Stack tecnológica](#stack-tecnológica)
- [Arquitetura](#arquitetura)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Pré-requisitos](#pré-requisitos)
- [Instalação local](#instalação-local)
- [Configuração](#configuração)
- [Banco de dados e migrations](#banco-de-dados-e-migrations)
- [Autenticação](#autenticação)
- [API](#api)
- [Regras de acesso](#regras-de-acesso)
- [Testes e qualidade](#testes-e-qualidade)
- [Docker](#docker)
- [Frontend](#frontend)
- [Segurança](#segurança)
- [Limitações conhecidas](#limitações-conhecidas)
- [Melhorias futuras](#melhorias-futuras)
- [Autor](#autor)

## Sobre

O HelpDesk API permite que usuários abram chamados, técnicos acompanhem e
resolvam atendimentos e administradores gerenciem categorias, usuários,
atribuições e permissões.

## Funcionalidades

- Cadastro e autenticação de usuários.
- Login OAuth2 Password Bearer com tokens JWT.
- Refresh tokens rotativos e logout com revogação de sessão.
- Senhas armazenadas com hash Argon2.
- Perfis `ADMIN`, `TECHNICIAN` e `USER`.
- Categorias ativas para classificação dos chamados.
- Tickets com status, prioridade, solicitante e técnico responsável.
- Filtros por status, prioridade, categoria, técnico, usuário e datas.
- Paginação e limite máximo de resultados.
- Comentários em tickets atendidos por técnicos.
- Notificações automáticas para administradores e técnicos.
- Registro de alterações importantes em `AuditLog`.
- Dashboard com contagens agregadas no banco de dados.
- SLA calculado por prioridade e indicador de chamados atrasados.
- Documentação OpenAPI gerada pelo FastAPI.

## Stack tecnológica

### Backend

- **Python 3.12+**: linguagem principal, com type hints e recursos modernos.
- **FastAPI**: framework HTTP assíncrono/síncrono, validação integrada e
	geração automática de OpenAPI.
- **Uvicorn**: servidor ASGI usado para executar a aplicação.

### Dados

- **PostgreSQL**: banco relacional principal para ambiente de produção.
- **SQLAlchemy 2**: ORM tipado para models, relacionamentos e consultas.
- **Alembic**: versionamento e aplicação das alterações do schema.
- **psycopg**: driver PostgreSQL para Python.

### Segurança

- **PyJWT**: criação e validação de tokens JWT.
- **pwdlib + Argon2**: hash seguro de senhas.
- **OAuth2 Password Bearer**: fluxo de autenticação documentado no Swagger.

### Qualidade e testes

- **Pydantic v2** e `email-validator`: validação dos payloads e emails.
- **Pytest** e **HTTPX**: testes unitários e de integração HTTP.
- **Ruff**: lint e verificação de imports.
- **Black**: formatação consistente.
- **isort**: ordenação dos imports.

## Arquitetura

O código é dividido por responsabilidade:

- `api/routes`: recebe requisições, aplica dependências e retorna respostas.
- `api/dependencies.py`: sessão de banco, autenticação e autorização por papel.
- `core`: configuração, segurança e conexão com o banco.
- `models`: entidades SQLAlchemy e relacionamentos.
- `schemas`: contratos de entrada e saída Pydantic.
- `repositories`: acesso reutilizável aos dados.
- `services`: operações de negócio reutilizáveis, como usuários e auditoria.
- `tests`: testes isolados com SQLite em memória.

As rotas não criam tabelas. O schema é controlado pelo Alembic e as tabelas são
criadas pela migration versionada.

## Estrutura do projeto

```text
helpdesk-api/
├── app/
│   ├── api/
│   │   ├── routes/
│   │   └── dependencies.py
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   └── security.py
│   ├── models/
│   ├── repositories/
│   ├── schemas/
│   ├── services/
│   └── main.py
├── alembic/
│   ├── env.py
│   └── versions/
├── tests/
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Pré-requisitos

Para execução local:

- Python 3.12 ou superior.
- PostgreSQL 16 ou compatível.
- Git, opcional para clonar o projeto.

Para execução com containers:

- Docker Engine ou Docker Desktop.
- Docker Compose v2.

## Instalação local

### Windows PowerShell

```powershell
Set-Location "C:\Users\User\Desktop\helpdesk-api"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

### Linux ou macOS

```bash
cd /caminho/para/helpdesk-api
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
cp .env.example .env
```

Edite o `.env` com os dados do PostgreSQL e uma chave JWT forte. Em seguida:

```bash
alembic upgrade head
uvicorn app.main:app --reload
```

No Windows, os mesmos comandos podem ser executados como
`python -m alembic upgrade head` e `python -m uvicorn app.main:app --reload`.

URLs disponíveis após iniciar:

- API: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- Healthcheck: `http://127.0.0.1:8000/health`
- Readiness: `http://127.0.0.1:8000/health/ready`

## Configuração

O arquivo `.env.example` é um modelo. Crie `.env` localmente, Variáveis suportadas:

| Variável | Obrigatória | Descrição |
| --- | --- | --- |
| `DATABASE_URL` | Sim | URL SQLAlchemy, por exemplo `postgresql+psycopg://usuario:senha@localhost:5432/banco` |
| `JWT_SECRET_KEY` | Sim | Segredo com no mínimo 32 caracteres |
| `JWT_ALGORITHM` | Não | Algoritmo JWT; padrão `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Não | Expiração do token; padrão `30` |
| `APP_NAME` | Não | Nome exibido no OpenAPI |
| `APP_VERSION` | Não | Versão exibida no OpenAPI |
| `DEBUG` | Não | Modo de debug; padrão `false` |
| `CORS_ORIGINS` | Não | Lista JSON de origens permitidas |

Exemplo mínimo de `.env`:

```dotenv
DATABASE_URL=postgresql+psycopg://helpdesk:senha-forte@localhost:5432/helpdesk
JWT_SECRET_KEY=gere-uma-chave-aleatoria-com-pelo-menos-32-caracteres
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
CORS_ORIGINS=["http://localhost:3000"]
```

## Banco de dados e migrations

A migration inicial cria:

- `users`: usuários, roles e estado da conta.
- `categories`: categorias de chamados.
- `tickets`: chamados, status, prioridade e referências.
- `ticket_comments`: comentários vinculados a ticket e usuário.
- `audit_logs`: histórico de ações relevantes.
- `notifications`: avisos pessoais lidos e não lidos.
- `sla_policies`: prazos de resolução configuráveis por prioridade.
- `refresh_tokens`: sessões renováveis e revogáveis.

As categorias iniciais disponíveis no formulário são:

- `Geral`: solicitações gerais de suporte.
- `Hardware`: computadores, periféricos e equipamentos.
- `Software`: sistemas, aplicativos e acessos.

Comandos principais:

```bash
alembic upgrade head       # aplicar todas as migrations
alembic downgrade -1       # voltar uma migration
alembic current            # mostrar a versão atual
alembic history             # listar o histórico
alembic revision --autogenerate -m "descricao da alteracao"
```

O `DATABASE_URL` do ambiente tem prioridade sobre o valor de
`alembic.ini`. A aplicação não chama `create_all` no startup.

## Autenticação

### Registrar usuário

`POST /auth/register` recebe JSON:

```json
{
	"name": "Ana Silva",
	"email": "ana@example.com",
	"password": "senha-com-8-caracteres"
}
```

### Fazer login

`POST /auth/login` usa `application/x-www-form-urlencoded`, compatível com
OAuth2:

```bash
curl -X POST http://127.0.0.1:8000/auth/login \
	-H "Content-Type: application/x-www-form-urlencoded" \
	-d "username=ana@example.com&password=senha-com-8-caracteres"
```

Resposta:

```json
{
	"access_token": "eyJ...",
	"token_type": "bearer"
}
```

Envie o token nas rotas protegidas:

```http
Authorization: Bearer eyJ...
```

O endpoint `GET /auth/me` retorna os dados públicos do usuário autenticado.
O `password_hash` nunca faz parte da resposta.
O frontend renova automaticamente o access token quando ele expira e revoga a
sessão no logout.

## API

Todas as rotas abaixo, exceto registro e login, exigem autenticação quando
indicadas como protegidas.

### Healthcheck

| Método | Rota | Acesso | Descrição |
| --- | --- | --- | --- |
| GET | `/health` | Público | Verifica se a aplicação está respondendo |

### Autenticação

| Método | Rota | Acesso | Descrição |
| --- | --- | --- | --- |
| POST | `/auth/register` | Público | Cria usuário comum |
| POST | `/auth/login` | Público | Gera access e refresh tokens |
| POST | `/auth/refresh` | Público | Renova a sessão com refresh token |
| POST | `/auth/logout` | Autenticado | Revoga o refresh token |
| GET | `/auth/me` | Autenticado | Retorna usuário atual |

### Usuários

| Método | Rota | Acesso | Descrição |
| --- | --- | --- | --- |
| GET | `/users` | Admin | Lista usuários |
| POST | `/users` | Admin | Cria usuário ou técnico |
| PATCH | `/users/{user_id}` | Admin | Atualiza nome, role ou ativo |
| DELETE | `/users/{user_id}` | Admin | Exclui conta sem histórico |

### Categorias

| Método | Rota | Acesso | Descrição |
| --- | --- | --- | --- |
| POST | `/categories` | Admin | Cria categoria |
| GET | `/categories` | Autenticado | Lista categorias ativas |
| GET | `/categories/{category_id}` | Autenticado | Consulta uma categoria |
| PUT | `/categories/{category_id}` | Admin | Atualiza categoria |

Payload de categoria:

```json
{
	"name": "Hardware",
	"description": "Computadores e periféricos"
}
```

### Tickets

| Método | Rota | Acesso | Descrição |
| --- | --- | --- | --- |
| POST | `/tickets` | Usuário | Cria chamado |
| GET | `/tickets` | Autenticado | Lista chamados visíveis |
| GET | `/tickets/{ticket_id}` | Conforme role | Consulta chamado |
| PUT | `/tickets/{ticket_id}` | Conforme role | Atualiza chamado aberto |
| PATCH | `/tickets/{ticket_id}/status` | Técnico/Admin | Altera status |
| PATCH | `/tickets/{ticket_id}/assign` | Admin | Atribui técnico |
| DELETE | `/tickets/{ticket_id}` | Admin | Exclui chamado |

Payload de criação:

```json
{
	"title": "Notebook não liga",
	"description": "O equipamento não inicia após pressionar o botão.",
	"priority": "HIGH",
	"category_id": 1
}
```

Valores aceitos:

- Status: `OPEN`, `IN_PROGRESS`, `WAITING_USER`, `RESOLVED`, `CLOSED`.
- Prioridade: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`.

Ao alterar para `RESOLVED`, `resolved_at` é preenchido e a nota de solução é
salva automaticamente como comentário do técnico. A nota é obrigatória e pode
registrar, por exemplo, “peça trocada” ou “SSD adicionado”. Ao reabrir para
outro status, `resolved_at` é removido. Tickets `CLOSED` não podem ser
alterados por esses fluxos normais.

### Comentários

| Método | Rota | Acesso | Descrição |
| --- | --- | --- | --- |
| POST | `/tickets/{ticket_id}/comments` | Usuário/Técnico/Admin | Adiciona comentário |
| GET | `/tickets/{ticket_id}/comments` | Conforme role | Lista comentários |
| GET | `/tickets/{ticket_id}/audit` | Conforme role | Consulta o histórico do chamado |

Payload:

```json
{
	"content": "O equipamento foi testado e está funcionando."
}
```

### Dashboard

`GET /dashboard` retorna total, abertos, em andamento, resolvidos, críticos e
atrasados e agregações por prioridade, categoria e técnico. Cada usuário visualiza apenas
os dados correspondentes ao seu escopo de acesso.

### Notificações

| Método | Rota | Acesso | Descrição |
| --- | --- | --- | --- |
| GET | `/notifications` | Autenticado | Lista os últimos avisos do usuário |
| PATCH | `/notifications/{notification_id}/read` | Dono do aviso | Marca uma notificação como lida |
| PATCH | `/notifications/read-all` | Autenticado | Marca todas como lidas |
| DELETE | `/notifications` | Autenticado | Limpa as notificações do usuário |

Um novo chamado gera um aviso para todos os administradores ativos. Quando o
administrador atribui um ticket, o técnico selecionado recebe um aviso. O
frontend consulta esses avisos automaticamente a cada cinco segundos e mostra
um contador e uma mensagem sem exigir atualização manual da página.

### SLA

| Método | Rota | Acesso | Descrição |
| --- | --- | --- | --- |
| GET | `/sla` | Autenticado | Lista as políticas atuais |
| PATCH | `/sla/{priority}` | Admin | Altera o prazo de uma prioridade |

Os prazos padrão são `CRITICAL=4`, `HIGH=8`, `MEDIUM=24` e `LOW=72` horas.
Chamados novos recebem o prazo correspondente à prioridade no momento da
criação. A API informa `sla_due_at` e `is_overdue` em cada ticket.

### Filtros, paginação e limite

Exemplo:

```text
GET /tickets?page=1&limit=20&status=OPEN&priority=HIGH&category=1
```

Parâmetros disponíveis:

| Parâmetro | Tipo | Observação |
| --- | --- | --- |
| `status` | enum | Status do ticket |
| `priority` | enum | Prioridade do ticket |
| `category` | inteiro positivo | ID da categoria |
| `technician` | inteiro positivo | ID do técnico |
| `user` | inteiro positivo | ID do solicitante, disponível para admin |
| `data_inicial` | `YYYY-MM-DD` | Data inicial de criação |
| `data_final` | `YYYY-MM-DD` | Data final de criação |
| `page` | inteiro >= 1 | Página; padrão `1` |
| `limit` | inteiro de 1 a 100 | Itens por página; padrão `20` |

## Regras de acesso

- Usuário comum cria e consulta apenas os próprios tickets.
- Administradores e técnicos não criam tickets; eles atuam nos tickets existentes.
- Técnico consulta tickets atribuídos a ele e altera seu status.
- Técnico adiciona comentários nos tickets atribuídos a ele.
- Usuário responde comentários apenas nos próprios tickets.
- Administrador consulta todos os tickets.
- Administrador cria/atualiza categorias, gerencia usuários e atribui técnicos.
- Somente técnicos existentes com role `TECHNICIAN` podem ser atribuídos.
- Tickets e categorias inexistentes retornam `404`.
- Dados inválidos retornam `422`.
- Email duplicado retorna `409`.
- Token inválido, expirado ou malformado retorna `401`.
- Acesso sem papel suficiente retorna `403`.

## Testes e qualidade

Os testes usam SQLite em memória e override da dependência de banco, permitindo
validar a API sem alterar um PostgreSQL de desenvolvimento.

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m pytest tests/test_auth.py -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m black --check .
.\.venv\Scripts\python.exe -m isort --check-only .
```

O conjunto atual cobre autenticação, JWT inválido, models, relacionamentos,
permissões, categorias, tickets, atribuição, comentários e dashboard.

## Docker

O `docker-compose.yml` contém três serviços:

- `backend`: executa migrations e inicia Uvicorn na porta `8000`.
- `postgres`: PostgreSQL 16 com volume persistente e healthcheck.
- `frontend`: Nginx servindo o portal na porta `3000`.

Configure as variáveis no terminal ou em um arquivo `.env` usado pelo Compose:

```powershell
$env:POSTGRES_USER = "helpdesk"
$env:POSTGRES_PASSWORD = "substitua-por-uma-senha-forte"
$env:POSTGRES_DB = "helpdesk"
$env:JWT_SECRET_KEY = "substitua-por-uma-chave-com-pelo-menos-32-caracteres"
docker compose up --build
```

O backend só inicia depois que o healthcheck do PostgreSQL passa. Para parar os
serviços:

```powershell
docker compose down
```

Para remover também os dados persistidos, use `docker compose down -v`.

Em uma instalação separada para cada empresa, cada cliente deve ter seu próprio
arquivo de ambiente, volume PostgreSQL e projeto Compose. O serviço `backend`
fica na porta `8000` e o serviço `frontend` na porta `3000`.

### Instalação isolada por empresa

Para instalar o produto em uma empresa:

1. Copie o projeto para um diretório exclusivo do cliente.
2. Crie um `.env` exclusivo para essa instalação.
3. Use um banco e um volume PostgreSQL exclusivos.
4. Defina uma `JWT_SECRET_KEY` nova e aleatória.
5. Suba os containers com `docker compose up --build -d`.
6. Verifique `http://localhost:8000/health/ready`.
7. Crie o primeiro usuário e promova-o a administrador pelo procedimento de bootstrap.
8. Entregue ao cliente o endereço do frontend, não as credenciais do banco.

Cada instalação deve usar valores diferentes para banco, senha, segredo JWT,
portas públicas e domínio. Não reutilize o `.env` de outra empresa.

### Quick start com Docker

No PowerShell, a partir da raiz do projeto:

```powershell
Copy-Item .env.example .env
# Edite .env e preencha os valores reais
docker compose up --build -d
docker compose ps
```

No Linux/macOS:

```bash
cp .env.example .env
# Edite .env e preencha os valores reais
docker compose up --build -d
docker compose ps
```

Para acompanhar os logs:

```bash
docker compose logs -f backend
```

## Frontend

O diretório `frontend/` contém um portal simples para usuários finais. Ele foi
feito em HTML, CSS e JavaScript sem dependências de Node, para poder ser usado
imediatamente no Windows. A tela permite criar conta, entrar, abrir chamado e
acompanhar os próprios tickets.

Com a API rodando em outro terminal, execute na raiz do projeto:

```powershell
python -m http.server 3000 --directory frontend
```

Abra:

```text
http://localhost:3000
```

O frontend chama a API em `http://127.0.0.1:8000`. Por isso, mantenha o
Uvicorn ativo e confirme que `CORS_ORIGINS` inclui `http://localhost:3000`.
O token de login é mantido apenas no `localStorage` do navegador para permitir
que o usuário navegue sem repetir o login durante a sessão local.

### Acesso administrativo

O botão `Administração` aparece automaticamente apenas para usuários com role
`ADMIN`. Para promover o primeiro usuário durante o desenvolvimento, execute
no Query Tool do pgAdmin, conectado ao banco `helpdesk`:

```sql
UPDATE users
SET role = 'ADMIN'
WHERE email = 'admito@example.com';
```

Saia do portal, entre novamente para receber um token atualizado e clique em
`Administração`. A página permite:

- listar todos os chamados;
- buscar por título ou descrição;
- filtrar por status e prioridade;
- alterar o status diretamente na tabela;
- atribuir um técnico ativo;
- excluir chamados.

Para atribuir tickets, deve existir pelo menos um usuário com role
`TECHNICIAN`. Essa promoção pode ser feita no pgAdmin:

```sql
UPDATE users
SET role = 'TECHNICIAN'
WHERE email = 'tecnico@example.com';
```

## Segurança

- Senhas nunca são armazenadas diretamente.
- O segredo JWT é obrigatório e não possui valor padrão previsível.
- Credenciais não devem ser colocadas no Git.
- `.env` está no `.gitignore`; apenas `.env.example` é versionado.
- CORS é configurável por ambiente.
- Payloads, enums, IDs, emails e paginação são validados pelo Pydantic.
- Autorização é aplicada por dependências antes das operações protegidas.
- Alterações importantes geram `AuditLog`.
- Refresh tokens são armazenados no banco somente como hash.
- Sessões podem ser renovadas e revogadas no logout.

## Troubleshooting

### `requirements.txt` não encontrado

O terminal está fora da raiz do projeto. Execute:

```powershell
Set-Location "C:\Users\User\Desktop\helpdesk-api"
```

### `No module named alembic.__main__`

O Python global está sendo usado. Ative o ambiente virtual:

```powershell
.\.venv\Scripts\Activate.ps1
python -m alembic upgrade head
```

### Falha de autenticação PostgreSQL

Confira se a senha do `DATABASE_URL` é a mesma senha configurada no PostgreSQL.
O serviço pode estar ativo e a porta `5432` aberta mesmo quando a senha está
incorreta.

### `DuplicateObject: type ... already exists`

Não execute `create_all` manualmente. Use a migration atualizada:

```powershell
python -m alembic upgrade head
```

### Frontend mostra `Failed to fetch`

Confirme que o backend está em `http://127.0.0.1:8000`, que o Uvicorn está
rodando e que `CORS_ORIGINS` contém `http://localhost:3000`.

### Frontend antigo ou botão ausente

Use `Ctrl + F5` ou abra a URL com o parâmetro de versão atual. O frontend usa
versionamento de assets para evitar cache durante o desenvolvimento.

## Screenshots

Como este é um backend, a principal interface de demonstração é o Swagger UI
em `/docs`, que é gerado automaticamente pela aplicação. Não há imagens
estáticas versionadas neste repositório.

## Limitações conhecidas

- A suíte automatizada não substitui um teste com PostgreSQL real.
- O ambiente precisa ter Docker instalado para executar `docker compose`.
- A listagem de tickets possui paginação e metadados, mas ainda não oferece
    filtros de texto server-side.
- Ainda não há rate limiting, anexos ou observabilidade completa.
- Não existe endpoint público de bootstrap de administrador; o primeiro admin
	deve ser promovido por operação administrativa no banco ou fluxo controlado
	de implantação.

Este repositório está pronto para demonstração e pilotos controlados. Antes de
uma operação crítica, valide PostgreSQL, Docker, backups, HTTPS, monitoramento,
recuperação de desastres e políticas de segurança no ambiente do cliente.

## Melhorias futuras

- Rate limiting e proteção contra abuso.
- Logs estruturados, métricas e tracing.
- Pipeline CI/CD e testes contra PostgreSQL em container.
- Upload de anexos e notificações por email.
- Endpoint de bootstrap seguro para o primeiro administrador.

## Autor

Projeto de portfólio desenvolvido para demonstrar uma API de suporte com
autenticação, autorização por papéis, persistência relacional e frontend web.

https://github.com/HericksonWillianCordeiro

https://www.linkedin.com/in/hericksonwcordeiro/