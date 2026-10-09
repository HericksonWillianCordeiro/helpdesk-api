# HelpDesk API — PHP Port (Branch `php-port`)

![PHP](https://img.shields.io/badge/PHP-8.2-777BB4?logo=php&logoColor=white)
![Symfony](https://img.shields.io/badge/Symfony-7.1-000000?logo=symfony&logoColor=white)
![Doctrine](https://img.shields.io/badge/Doctrine_ORM-3.2-FC6A31?logo=doctrine&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?logo=postgresql&logoColor=white)
![PHPUnit](https://img.shields.io/badge/PHPUnit-11-6C3EB3)

> **Esta branch é um port do projeto principal (Python/FastAPI) para PHP com Symfony 7 + Doctrine ORM.**
> O objetivo é demonstrar que os mesmos conceitos arquiteturais — repositories, services, migrations, JWT, testes unitários — se aplicam independentemente da linguagem.

---

## Comparativo Python → PHP

| Conceito | Python (main) | PHP (esta branch) |
|---|---|---|
| Framework | FastAPI | Symfony 7 |
| ORM | SQLAlchemy 2 | Doctrine ORM 3 |
| Migrations | Alembic | Doctrine Migrations |
| Validação | Pydantic v2 | Symfony Validator |
| Auth JWT | PyJWT | firebase/php-jwt |
| Hash de senha | Argon2 (pwdlib) | `password_hash(PASSWORD_ARGON2ID)` |
| Testes | Pytest + HTTPX | PHPUnit 11 |
| Contêiner | Uvicorn/ASGI | Symfony + PHP-FPM |

---

## O que está implementado neste port

- ✅ Entidades com Doctrine ORM (`User`, `Ticket`, `Category`, `TicketComment`)
- ✅ Repositories com queries customizadas (filtros, paginação, dashboard)
- ✅ `AuthService` — registro com Argon2ID, login, geração e validação de JWT
- ✅ `TicketService` — CRUD, mudança de status, atribuição, SLA, comentários
- ✅ Controllers REST com Symfony (`AuthController`, `TicketController`)
- ✅ Testes unitários com PHPUnit (`TicketTest`, `AuthServiceTest`)
- ✅ Mesmas regras de acesso por papel (USER / TECHNICIAN / ADMIN)
- ✅ SLA calculado por prioridade (CRITICAL=4h, HIGH=8h, MEDIUM=24h, LOW=72h)

### O que não está neste port (existe no projeto Python)
- Refresh tokens rotativos (foco do port é demonstrar a arquitetura core)
- AuditLog
- Notificações
- Docker Compose configurado para PHP
- Frontend

---

## Estrutura do projeto

```
php-port/
├── src/
│   ├── Controller/        # AuthController, TicketController
│   ├── Entity/            # User, Ticket, Category, TicketComment (Doctrine ORM)
│   ├── Repository/        # Queries customizadas com QueryBuilder
│   └── Service/           # AuthService, TicketService (lógica de negócio)
├── tests/
│   └── Unit/              # TicketTest, AuthServiceTest (PHPUnit)
├── migrations/            # Doctrine Migrations (versionamento de schema)
├── config/                # Configurações Symfony
├── composer.json
└── README.md
```

---

## Como rodar

### Pré-requisitos
- PHP 8.2+
- Composer
- PostgreSQL 15+

### Instalação

```bash
cd php-port

# Instalar dependências
composer install

# Copiar e configurar variáveis de ambiente
cp .env.example .env
# Edite .env com DATABASE_URL e JWT_SECRET

# Criar banco e rodar migrations
php bin/console doctrine:database:create
php bin/console doctrine:migrations:migrate

# Iniciar servidor
php -S localhost:8001 -t public/
```

A API estará em `http://localhost:8001/api`

---

## Testes

```bash
cd php-port

# Rodar todos os testes unitários
./vendor/bin/phpunit tests/Unit/ --colors=always

# Com cobertura de código
./vendor/bin/phpunit tests/Unit/ --coverage-text
```

---

## Endpoints disponíveis

| Método | Rota | Acesso | Descrição |
|--------|------|--------|-----------|
| POST | `/api/auth/register` | Público | Cadastro |
| POST | `/api/auth/login` | Público | Login + JWT |
| GET | `/api/auth/me` | Autenticado | Usuário atual |
| GET | `/api/tickets` | Autenticado | Lista com filtros |
| POST | `/api/tickets` | USER | Abre chamado |
| GET | `/api/tickets/{id}` | Autenticado | Detalhe |
| PATCH | `/api/tickets/{id}/status` | TECH/ADMIN | Altera status |
| PATCH | `/api/tickets/{id}/assign` | ADMIN | Atribui técnico |
| DELETE | `/api/tickets/{id}` | ADMIN | Remove |
| POST | `/api/tickets/{id}/comments` | Autenticado | Comenta |
| GET | `/api/tickets/dashboard` | Autenticado | Estatísticas |

---

## Decisões de design

**Por que Symfony em vez de PHP puro?**
A vaga menciona Symfony como diferencial. O Symfony traz injeção de dependência nativa, roteamento por atributos PHP 8, integração direta com Doctrine e uma suíte de testes robusta — tudo que o projeto precisa sem reinventar a roda.

**Por que Doctrine ORM?**
A vaga menciona Doctrine ORM/DBAL como diferencial. O Doctrine oferece o padrão Repository que já estava no projeto Python (SQLAlchemy), tornando a migração conceitual direta.

**Por que Argon2ID e não bcrypt?**
`PASSWORD_ARGON2ID` é o algoritmo recomendado pelo PHP 8.2+ para novos projetos. Mantém paridade com o projeto Python que usa `pwdlib + Argon2`.

---

Desenvolvido por **Herickson Willian Cordeiro**
