# Getting Started with CloudGuard

This guide will help you set up and run CloudGuard locally for development.

## Prerequisites

- **Docker** & **Docker Compose** (recommended for quick start)
- OR manually install:
  - Python 3.9+
  - Node.js 16+
  - PostgreSQL 14+
  - Redis 6+
  - RabbitMQ 3+

## Quick Start with Docker (Recommended)

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/cloudguard.git
cd cloudguard
```

### 2. Set Up Environment Variables

```bash
# Copy example environment file
cp backend/.env.example backend/.env

# Edit backend/.env with your settings
# At minimum, update SECRET_KEY and JWT_SECRET_KEY
```

### 3. Start All Services

```bash
# Start all services (database, cache, queue, backend, frontend)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### 4. Access the Application

- **Frontend Dashboard**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/api/docs
- **RabbitMQ Management**: http://localhost:15672 (guest/guest)

### 5. Initialize the Database

```bash
# Create database tables
docker-compose exec backend python -c "from app.core.database import init_db; init_db()"

# (Optional) Seed with sample data
docker-compose exec backend python scripts/seed_data.py
```

---

## Manual Setup (Without Docker)

### 1. Set Up Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your settings

# Initialize database
python -c "from app.core.database import init_db; init_db()"

# Run backend
uvicorn app.main:app --reload
```

### 2. Set Up Frontend

```bash
cd frontend

# Install dependencies
npm install

# Run frontend
npm run dev
```

### 3. Start Background Workers

```bash
cd backend
source venv/bin/activate

# Start Celery worker
celery -A app.tasks worker --loglevel=info
```

### 4. Install & Start Required Services

**PostgreSQL:**
```bash
# Install PostgreSQL 14+
# Create database
createdb cloudguard

# Install TimescaleDB extension
psql cloudguard -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"
```

**Redis:**
```bash
# Install and start Redis
redis-server
```

**RabbitMQ:**
```bash
# Install and start RabbitMQ
rabbitmq-server
```

---

## Connecting Your AWS Account

### 1. Create IAM Role in AWS

Create an IAM role in your AWS account with the following:

**Trust Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::YOUR_CLOUDGUARD_ACCOUNT:root"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "sts:ExternalId": "YOUR_UNIQUE_EXTERNAL_ID"
        }
      }
    }
  ]
}
```

**Attach Policy:**
Use the read-only policy template from `docs/aws-iam-policy.json`

### 2. Add Account via API

```bash
curl -X POST http://localhost:8000/api/v1/accounts \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "aws_account_id": "123456789012",
    "aws_account_name": "Production",
    "role_arn": "arn:aws:iam::123456789012:role/CloudGuardRole",
    "external_id": "YOUR_UNIQUE_EXTERNAL_ID"
  }'
```

### 3. Run Initial Scan

```bash
curl -X POST http://localhost:8000/api/v1/accounts/{account_id}/scan \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Project Structure

```
cloudguard/
├── backend/                 # Python FastAPI backend
│   ├── app/
│   │   ├── api/            # API endpoints
│   │   ├── core/           # Core configuration
│   │   ├── models/         # Database models
│   │   ├── services/       # Business logic
│   │   └── utils/          # Utilities
│   ├── tests/              # Backend tests
│   └── requirements.txt    # Python dependencies
│
├── frontend/               # React TypeScript frontend
│   ├── src/
│   │   ├── components/     # Reusable components
│   │   ├── pages/          # Page components
│   │   ├── services/       # API clients
│   │   ├── hooks/          # Custom React hooks
│   │   └── utils/          # Utilities
│   └── package.json        # Node dependencies
│
├── docs/                   # Documentation
├── docker-compose.yml      # Docker setup
└── README.md              # Main README
```

---

## Development Workflow

### Running Tests

**Backend:**
```bash
cd backend
pytest

# With coverage
pytest --cov=app tests/
```

**Frontend:**
```bash
cd frontend
npm test

# With coverage
npm test -- --coverage
```

### Code Quality

**Backend:**
```bash
# Format code
black app/

# Lint
flake8 app/

# Type check
mypy app/
```

**Frontend:**
```bash
# Lint
npm run lint

# Type check
npm run type-check
```

### Database Migrations

```bash
cd backend

# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

---

## Common Issues & Solutions

### Issue: Database Connection Failed

**Solution:**
- Verify PostgreSQL is running: `pg_isready`
- Check DATABASE_URL in `.env`
- Ensure database exists: `createdb cloudguard`

### Issue: Frontend Can't Connect to Backend

**Solution:**
- Verify backend is running on port 8000
- Check CORS settings in `backend/app/core/config.py`
- Ensure VITE_API_URL is correct in frontend

### Issue: AWS Authentication Failed

**Solution:**
- Verify IAM role ARN is correct
- Check external ID matches
- Ensure role has required permissions
- Test with AWS CLI: `aws sts assume-role --role-arn ... --role-session-name test`

### Issue: Celery Worker Not Processing Tasks

**Solution:**
- Verify RabbitMQ is running
- Check CELERY_BROKER_URL in `.env`
- Restart worker: `celery -A app.tasks worker --loglevel=debug`

---

## Next Steps

1. **[Implementation Guide](IMPLEMENTATION_GUIDE.md)** - Detailed build instructions
2. **[Architecture](ARCHITECTURE.md)** - System design and architecture
3. **[Market Analysis](MARKET_ANALYSIS.md)** - Business viability and market research
4. **[API Documentation](http://localhost:8000/api/docs)** - Interactive API docs

---

## Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/cloudguard/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/cloudguard/discussions)
- **Email**: support@cloudguard.io

---

## License

This project is licensed under the MIT License - see [LICENSE](../LICENSE) file for details.
