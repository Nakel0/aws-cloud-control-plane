# Your Next Steps - Action Plan

## 🚀 Phase 1: Get It Running (TODAY - 30 minutes)

### 1. Set Up Environment Variables

```bash
cd /workspace

# Copy the example environment file
cp backend/.env.example backend/.env

# Generate secure keys
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"
python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(32))"

# Edit backend/.env and paste the generated keys
nano backend/.env  # or use your preferred editor
```

**Required changes in `.env`:**
```bash
SECRET_KEY=<paste-generated-key-here>
JWT_SECRET_KEY=<paste-generated-key-here>
DEBUG=true
ENV=development
```

### 2. Start All Services

```bash
# Start everything with Docker
docker-compose up -d

# Check that all services are running
docker-compose ps

# You should see: postgres, redis, rabbitmq, backend, frontend, worker
```

### 3. Initialize Database

```bash
# Create database tables
docker-compose exec backend python -c "from app.core.database import init_db; init_db()"

# Optional: Convert cost_data table to TimescaleDB hypertable
docker-compose exec postgres psql -U cloudguard -d cloudguard -c "SELECT create_hypertable('cost_data', 'time', if_not_exists => TRUE);"
```

### 4. Verify Everything Works

```bash
# Test backend health
curl http://localhost:8000/health
# Should return: {"status":"healthy",...}

# Open frontend in browser
open http://localhost:3000
# Should show the dashboard

# View API documentation
open http://localhost:8000/api/docs
```

### 5. View Logs (Troubleshooting)

```bash
# View all logs
make logs

# Or view specific service
docker-compose logs backend
docker-compose logs frontend
docker-compose logs postgres
```

**🎉 If all above works, you're ready for Phase 2!**

---

## 🔧 Phase 2: Build API Endpoints (NEXT - Week 1-2)

This is the **most critical** next step. You need API endpoints to connect the frontend to the backend.

### Priority 1: Authentication Endpoints (Day 1-2)

Create `backend/app/api/auth.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from app.core.database import get_db
from app.core.security import (
    verify_password, 
    create_access_token, 
    create_refresh_token,
    get_current_user
)
from app.core.config import settings

router = APIRouter()

@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login endpoint - returns access and refresh tokens"""
    # TODO: Implement user lookup from database
    # For now, hardcoded demo user
    if form_data.username != "demo@cloudguard.io" or form_data.password != "demo123":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    # Create tokens
    access_token = create_access_token(
        data={"sub": "demo-user-id", "email": form_data.username, "role": "admin"}
    )
    refresh_token = create_refresh_token(
        data={"sub": "demo-user-id"}
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.get("/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user information"""
    return {
        "user_id": current_user.get("sub"),
        "email": current_user.get("email"),
        "role": current_user.get("role")
    }

@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """Logout endpoint"""
    # TODO: Blacklist token in Redis
    return {"message": "Successfully logged out"}
```

**Then add to `backend/app/main.py`:**

```python
from app.api import auth

app.include_router(auth.router, prefix=f"/api/{settings.API_VERSION}/auth", tags=["Authentication"])
```

### Priority 2: Account Management Endpoints (Day 3-4)

Create `backend/app/api/accounts.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import Account, AccountStatus
from app.services.aws_client import AWSClient

router = APIRouter()

@router.get("/")
async def list_accounts(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List all AWS accounts"""
    customer_id = current_user.get("sub")  # User ID
    accounts = db.query(Account).filter(Account.customer_id == customer_id).all()
    return [account.to_dict() for account in accounts]

@router.post("/")
async def create_account(
    aws_account_id: str,
    aws_account_name: str,
    role_arn: str,
    external_id: str = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Add a new AWS account"""
    customer_id = current_user.get("sub")
    
    # Test AWS connection
    aws_client = AWSClient(role_arn, external_id)
    connection_test = aws_client.test_connection()
    
    if not connection_test["success"]:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to connect to AWS account: {connection_test.get('error')}"
        )
    
    # Create account record
    account = Account(
        customer_id=customer_id,
        aws_account_id=aws_account_id,
        aws_account_name=aws_account_name,
        role_arn=role_arn,
        external_id=external_id,
        status=AccountStatus.ACTIVE
    )
    
    db.add(account)
    db.commit()
    db.refresh(account)
    
    return account.to_dict()

@router.get("/{account_id}")
async def get_account(
    account_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get account details"""
    account = db.query(Account).filter(Account.id == account_id).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    return account.to_dict()

@router.post("/{account_id}/scan")
async def trigger_scan(
    account_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Trigger a full scan of the AWS account"""
    account = db.query(Account).filter(Account.id == account_id).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # TODO: Trigger Celery task for scanning
    # from app.tasks import scan_account
    # scan_account.delay(str(account_id))
    
    return {"message": "Scan initiated", "account_id": str(account_id)}
```

### Priority 3: Cost Analysis Endpoints (Day 5-6)

Create `backend/app/api/cost.py`:

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import Account, CostData
from app.services.cost_analyzer import CostAnalyzer
from app.services.aws_client import AWSClient

router = APIRouter()

@router.get("/{account_id}/summary")
async def get_cost_summary(
    account_id: UUID,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get cost summary for the account"""
    account = db.query(Account).filter(Account.id == account_id).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Get cost data from database
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    cost_data = db.query(CostData).filter(
        CostData.account_id == account_id,
        CostData.time >= start_date,
        CostData.time <= end_date
    ).all()
    
    # Calculate summary
    total_cost = sum(item.cost for item in cost_data)
    
    return {
        "account_id": str(account_id),
        "period_days": days,
        "total_cost": float(total_cost),
        "daily_average": float(total_cost / days) if days > 0 else 0,
        "data_points": len(cost_data)
    }

@router.post("/{account_id}/analyze")
async def analyze_costs(
    account_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Run cost analysis and find optimization opportunities"""
    account = db.query(Account).filter(Account.id == account_id).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Initialize cost analyzer
    aws_client = AWSClient(account.role_arn, account.external_id)
    analyzer = CostAnalyzer(aws_client)
    
    # Run analysis
    recommendations = []
    recommendations.extend(analyzer.detect_idle_ec2_instances())
    recommendations.extend(analyzer.detect_unattached_ebs_volumes())
    recommendations.extend(analyzer.detect_unused_elastic_ips())
    recommendations.extend(analyzer.analyze_reserved_instance_opportunities())
    
    # Calculate total potential savings
    total_savings = sum(
        float(rec.get("potential_savings", 0)) 
        for rec in recommendations
    )
    
    return {
        "account_id": str(account_id),
        "recommendations_count": len(recommendations),
        "total_potential_savings": total_savings,
        "recommendations": recommendations
    }
```

### Priority 4: Security Endpoints (Day 7-8)

Create `backend/app/api/security.py`:

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import Account, SecurityFinding, Severity, FindingStatus
from app.services.security_scanner import SecurityScanner
from app.services.aws_client import AWSClient

router = APIRouter()

@router.get("/{account_id}/findings")
async def list_security_findings(
    account_id: UUID,
    severity: Optional[Severity] = None,
    status: Optional[FindingStatus] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List security findings for an account"""
    query = db.query(SecurityFinding).filter(
        SecurityFinding.account_id == account_id
    )
    
    if severity:
        query = query.filter(SecurityFinding.severity == severity)
    
    if status:
        query = query.filter(SecurityFinding.status == status)
    
    findings = query.offset(offset).limit(limit).all()
    total = query.count()
    
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "findings": [f.to_dict() for f in findings]
    }

@router.post("/{account_id}/scan")
async def run_security_scan(
    account_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Run security scan on the account"""
    account = db.query(Account).filter(Account.id == account_id).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Initialize security scanner
    aws_client = AWSClient(account.role_arn, account.external_id)
    scanner = SecurityScanner(aws_client)
    
    # Run full scan
    findings = scanner.run_full_scan()
    
    # Save findings to database
    for finding_data in findings:
        finding = SecurityFinding(
            account_id=account_id,
            **finding_data
        )
        db.add(finding)
    
    db.commit()
    
    # Calculate summary
    severity_counts = {}
    for finding in findings:
        sev = finding.get("severity")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
    
    return {
        "account_id": str(account_id),
        "findings_count": len(findings),
        "severity_breakdown": severity_counts
    }
```

### Priority 5: Update Main App (Day 9)

Update `backend/app/main.py` to include all routers:

```python
from app.api import auth, accounts, cost, security

# Add these lines after creating the app
app.include_router(auth.router, prefix=f"/api/{settings.API_VERSION}/auth", tags=["Authentication"])
app.include_router(accounts.router, prefix=f"/api/{settings.API_VERSION}/accounts", tags=["Accounts"])
app.include_router(cost.router, prefix=f"/api/{settings.API_VERSION}/cost", tags=["Cost"])
app.include_router(security.router, prefix=f"/api/{settings.API_VERSION}/security", tags=["Security"])
```

### Priority 6: Test API Endpoints (Day 10)

```bash
# Test authentication
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=demo@cloudguard.io&password=demo123"

# Save the access token
TOKEN="<your-access-token>"

# Test getting current user
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN"

# Test listing accounts
curl http://localhost:8000/api/v1/accounts \
  -H "Authorization: Bearer $TOKEN"

# Or use the interactive API docs
open http://localhost:8000/api/docs
```

---

## 🎨 Phase 3: Connect Frontend to Backend (Week 2)

### Step 1: Create API Client Service

Create `frontend/src/services/api.ts`:

```typescript
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Create axios instance
export const api = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// API methods
export const authAPI = {
  login: (username: string, password: string) =>
    api.post('/auth/login', 
      new URLSearchParams({ username, password }),
      { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
    ),
  getCurrentUser: () => api.get('/auth/me'),
};

export const accountsAPI = {
  list: () => api.get('/accounts'),
  get: (id: string) => api.get(`/accounts/${id}`),
  create: (data: any) => api.post('/accounts', data),
  scan: (id: string) => api.post(`/accounts/${id}/scan`),
};

export const costAPI = {
  getSummary: (accountId: string, days: number = 30) =>
    api.get(`/cost/${accountId}/summary?days=${days}`),
  analyze: (accountId: string) =>
    api.post(`/cost/${accountId}/analyze`),
};

export const securityAPI = {
  listFindings: (accountId: string, params?: any) =>
    api.get(`/security/${accountId}/findings`, { params }),
  scan: (accountId: string) =>
    api.post(`/security/${accountId}/scan`),
};
```

### Step 2: Update Dashboard with Real Data

Then update `frontend/src/pages/Dashboard.tsx` to use the API:

```typescript
import { useQuery } from '@tanstack/react-query';
import { accountsAPI, costAPI, securityAPI } from '@/services/api';

export default function Dashboard() {
  // Fetch accounts
  const { data: accounts } = useQuery({
    queryKey: ['accounts'],
    queryFn: () => accountsAPI.list().then(res => res.data),
  });

  // Get first account ID (for demo)
  const accountId = accounts?.[0]?.id;

  // Fetch cost summary
  const { data: costSummary } = useQuery({
    queryKey: ['cost-summary', accountId],
    queryFn: () => costAPI.getSummary(accountId).then(res => res.data),
    enabled: !!accountId,
  });

  // ... rest of component using real data
}
```

---

## 📅 Recommended Timeline

### Week 1: API Endpoints
- **Day 1-2**: Authentication endpoints
- **Day 3-4**: Account management
- **Day 5-6**: Cost analysis endpoints
- **Day 7-8**: Security endpoints
- **Day 9**: Integration & testing
- **Day 10**: Documentation

### Week 2: Frontend Integration
- **Day 1-2**: Create API client service
- **Day 3-4**: Update Dashboard with real data
- **Day 5-6**: Update Cost & Security pages
- **Day 7**: Testing & bug fixes
- **Day 8-10**: Polish & improvements

### Week 3-4: Background Jobs (Celery)
- **Day 1-2**: Set up Celery tasks structure
- **Day 3-4**: Cost data collection task
- **Day 5-6**: Security scanning task
- **Day 7-8**: Resource discovery task
- **Day 9-10**: Testing & monitoring

### Week 5-6: Complete MVP Features
- Reliability monitoring
- Automation engine
- Additional polish

---

## 🎯 Success Criteria

After completing the above, you should be able to:

✅ Login to the dashboard
✅ Add an AWS account
✅ See real cost data
✅ View security findings
✅ Get optimization recommendations
✅ Trigger scans manually

---

## 💡 Pro Tips

1. **Start Small**: Get authentication working first, then add features incrementally
2. **Test Often**: Use the interactive API docs at `/api/docs`
3. **Use Git**: Commit after each major feature
4. **Read Errors**: Error messages in FastAPI are very helpful
5. **Check Logs**: Use `make logs` when something doesn't work

---

## 🆘 If You Get Stuck

1. Check the logs: `docker-compose logs backend`
2. Review the API docs: http://localhost:8000/api/docs
3. Verify database: `make shell-db`
4. Test AWS connection independently
5. Ask for help (GitHub Issues)

---

## 📚 Reference Documentation

While building:
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **React Query**: https://tanstack.com/query/latest
- **Boto3 Docs**: https://boto3.amazonaws.com/v1/documentation/api/latest/index.html
- **SQLAlchemy**: https://docs.sqlalchemy.org/

---

## ✅ Checklist

Copy this to track your progress:

### Phase 1: Setup
- [ ] Environment variables configured
- [ ] Docker containers running
- [ ] Database initialized
- [ ] Frontend loads in browser
- [ ] Backend health check passes

### Phase 2: API Endpoints
- [ ] Authentication endpoints (login, logout, me)
- [ ] Account management (list, create, get)
- [ ] Cost analysis (summary, analyze)
- [ ] Security scanning (list findings, run scan)
- [ ] All endpoints tested in API docs

### Phase 3: Frontend Integration
- [ ] API client service created
- [ ] Authentication flow working
- [ ] Dashboard shows real data
- [ ] Cost page working
- [ ] Security page working

### Phase 4: Background Jobs
- [ ] Celery tasks structure
- [ ] Cost data collection
- [ ] Security scanning task
- [ ] Resource discovery

---

**You're on your way to building something amazing! 🚀**

Next file to create: `backend/app/api/auth.py`
