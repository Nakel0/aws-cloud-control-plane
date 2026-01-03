# Project Structure

## Recommended Project Layout

```
unified-cloud-platform/
├── README.md
├── QUICK_START.md
├── docs/
│   ├── IMPLEMENTATION_GUIDE.md
│   ├── MARKET_ANALYSIS.md
│   └── TECHNICAL_ARCHITECTURE.md
│
├── backend/                    # Backend API (Python FastAPI or Node.js NestJS)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py            # FastAPI app entry point
│   │   ├── config.py          # Configuration
│   │   ├── database.py        # Database connection
│   │   │
│   │   ├── api/               # API routes
│   │   │   └── v1/
│   │   │       ├── accounts.py
│   │   │       ├── cost.py
│   │   │       ├── security.py
│   │   │       └── reliability.py
│   │   │
│   │   ├── services/          # Business logic
│   │   │   ├── cost_service.py
│   │   │   ├── security_service.py
│   │   │   ├── reliability_service.py
│   │   │   └── aws_client.py
│   │   │
│   │   ├── models/            # Database models
│   │   │   ├── account.py
│   │   │   ├── cost.py
│   │   │   ├── security.py
│   │   │   └── reliability.py
│   │   │
│   │   ├── utils/             # Utilities
│   │   │   ├── aws.py
│   │   │   ├── encryption.py
│   │   │   └── validators.py
│   │   │
│   │   └── workers/           # Background workers
│   │       ├── cost_collector.py
│   │       ├── security_scanner.py
│   │       └── metrics_collector.py
│   │
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── fixtures/
│   │
│   ├── migrations/            # Database migrations
│   │   └── versions/
│   │
│   ├── requirements.txt       # Python dependencies
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── frontend/                   # Frontend (Next.js)
│   ├── app/                   # Next.js app directory
│   │   ├── layout.tsx
│   │   ├── page.tsx           # Home page
│   │   ├── dashboard/
│   │   │   └── page.tsx
│   │   ├── cost/
│   │   │   └── page.tsx
│   │   ├── security/
│   │   │   └── page.tsx
│   │   └── reliability/
│   │       └── page.tsx
│   │
│   ├── components/
│   │   ├── ui/                # Reusable UI components
│   │   ├── charts/
│   │   ├── tables/
│   │   └── forms/
│   │
│   ├── lib/
│   │   ├── api.ts             # API client
│   │   ├── utils.ts
│   │   └── hooks.ts
│   │
│   ├── public/
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   └── next.config.js
│
├── infrastructure/            # Infrastructure as Code
│   ├── terraform/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   ├── vpc.tf
│   │   ├── ecs.tf
│   │   ├── rds.tf
│   │   └── s3.tf
│   │
│   └── scripts/
│       ├── deploy.sh
│       └── setup.sh
│
├── lambda/                    # AWS Lambda functions
│   ├── cost-collector/
│   │   ├── lambda_function.py
│   │   └── requirements.txt
│   ├── security-scanner/
│   │   ├── lambda_function.py
│   │   └── requirements.txt
│   └── metrics-collector/
│       ├── lambda_function.py
│       └── requirements.txt
│
├── scripts/                   # Utility scripts
│   ├── setup_db.sh
│   ├── seed_data.py
│   └── run_migrations.sh
│
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── deploy.yml
│
├── .gitignore
├── docker-compose.yml          # Local development
└── Makefile                    # Common commands
```

## Key Files Explained

### Backend

- **`app/main.py`**: FastAPI application entry point, route registration
- **`app/config.py`**: Environment variables, configuration settings
- **`app/database.py`**: SQLAlchemy database session management
- **`app/api/v1/`**: REST API endpoints organized by domain
- **`app/services/`**: Business logic, AWS SDK integration
- **`app/models/`**: SQLAlchemy ORM models
- **`app/workers/`**: Background job processors

### Frontend

- **`app/`**: Next.js 13+ app directory (routing)
- **`components/`**: Reusable React components
- **`lib/api.ts`**: Axios/fetch wrapper for API calls
- **`public/`**: Static assets

### Infrastructure

- **`terraform/`**: Infrastructure as Code for AWS
- **`lambda/`**: Serverless functions for data collection

## Development Workflow

1. **Local Development**
   ```bash
   # Backend
   cd backend
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   
   # Frontend
   cd frontend
   npm install
   npm run dev
   ```

2. **Database Migrations**
   ```bash
   alembic revision --autogenerate -m "description"
   alembic upgrade head
   ```

3. **Testing**
   ```bash
   pytest  # Backend
   npm test  # Frontend
   ```

4. **Deployment**
   ```bash
   terraform apply  # Infrastructure
   ./scripts/deploy.sh  # Application
   ```

## Environment Variables

Create `.env` files:

**Backend `.env`:**
```bash
DATABASE_URL=postgresql://user:pass@localhost:5432/cloudplatform
AWS_REGION=us-east-1
SECRET_KEY=your-secret-key
JWT_SECRET=your-jwt-secret
REDIS_URL=redis://localhost:6379
```

**Frontend `.env.local`:**
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME=Cloud Platform
```

## Docker Setup

**`docker-compose.yml`:**
```yaml
version: '3.8'

services:
  db:
    image: timescale/timescaledb:latest-pg15
    environment:
      POSTGRES_DB: cloudplatform
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
  
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
  
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://postgres:postgres@db:5432/cloudplatform
      REDIS_URL: redis://redis:6379
    depends_on:
      - db
      - redis
  
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
    depends_on:
      - backend
```

## Makefile Commands

**`Makefile`:**
```makefile
.PHONY: install dev test deploy

install:
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

dev:
	docker-compose up

test:
	cd backend && pytest
	cd frontend && npm test

migrate:
	cd backend && alembic upgrade head

deploy:
	terraform apply
	./scripts/deploy.sh
```

## Next Steps

1. Create this directory structure
2. Initialize git repository
3. Set up development environment
4. Start with backend API (see QUICK_START.md)
5. Build frontend dashboard
6. Deploy to AWS

See [QUICK_START.md](./QUICK_START.md) for detailed implementation steps.
