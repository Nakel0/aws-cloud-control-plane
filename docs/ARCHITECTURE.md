# CloudGuard Platform Architecture

## System Overview

CloudGuard is a cloud-native, microservices-based platform designed for scalability, reliability, and security.

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        Load Balancer (ALB)                       │
└───────────────────────────┬──────────────────────────────────────┘
                            │
                ┌───────────┴───────────┐
                │                       │
        ┌───────▼────────┐     ┌───────▼────────┐
        │  Web Dashboard │     │   API Gateway  │
        │   (CloudFront) │     │    (FastAPI)   │
        │   React SPA    │     │                │
        └────────────────┘     └───────┬────────┘
                                       │
        ┌──────────────────────────────┼────────────────────────────┐
        │                              │                            │
┌───────▼────────┐        ┌───────────▼──────────┐    ┌───────────▼─────────┐
│  Cost Service  │        │  Security Service    │    │  Reliability Service│
│  - Analyzer    │        │  - Scanner           │    │  - Health Monitor   │
│  - Forecaster  │        │  - Compliance        │    │  - Predictor        │
│  - Optimizer   │        │  - Vulnerability DB  │    │  - Best Practices   │
└────────┬───────┘        └───────────┬──────────┘    └───────────┬─────────┘
         │                            │                            │
         └────────────────────────────┼────────────────────────────┘
                                      │
                         ┌────────────▼────────────┐
                         │  Automation Service     │
                         │  - Remediation Engine   │
                         │  - Workflow Manager     │
                         │  - Approval System      │
                         └────────────┬────────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        │                             │                             │
┌───────▼────────┐        ┌───────────▼──────────┐    ┌───────────▼─────────┐
│   PostgreSQL   │        │      Redis           │    │    RabbitMQ         │
│  (TimescaleDB) │        │   - Cache            │    │  - Task Queue       │
│  - Relational  │        │   - Session Store    │    │  - Event Bus        │
│  - Time-series │        │   - Rate Limiting    │    │                     │
└────────┬───────┘        └──────────────────────┘    └─────────────────────┘
         │
         │                 ┌────────────────────────────────────────┐
         └────────────────►│         Celery Workers                 │
                           │  - Data Collection Jobs                │
                           │  - Scanning Jobs                       │
                           │  - Automation Execution                │
                           └───────────────┬────────────────────────┘
                                           │
                                  ┌────────▼────────┐
                                  │   AWS Services  │
                                  │  - Cost Explorer│
                                  │  - EC2, RDS, S3 │
                                  │  - IAM, Config  │
                                  │  - CloudWatch   │
                                  └─────────────────┘
```

## Component Details

### 1. Frontend Layer

**Web Dashboard (React + TypeScript)**
- **Purpose**: User interface for all platform features
- **Technology**: 
  - React 18 with TypeScript
  - Tailwind CSS for styling
  - Recharts for data visualization
  - React Query for data fetching
  - Zustand for state management
- **Features**:
  - Real-time updates via WebSocket
  - Responsive design (desktop & mobile)
  - Dark/light mode
  - Export functionality (PDF, CSV)
- **Hosting**: CloudFront + S3 for CDN distribution

### 2. API Gateway

**FastAPI Backend**
- **Purpose**: Main API server handling all client requests
- **Technology**: Python FastAPI with async support
- **Responsibilities**:
  - Authentication & Authorization (JWT)
  - Request validation & sanitization
  - Rate limiting
  - API versioning
  - WebSocket connections
- **Endpoints**:
  - `/api/v1/auth/*` - Authentication
  - `/api/v1/accounts/*` - AWS account management
  - `/api/v1/cost/*` - Cost data and analysis
  - `/api/v1/security/*` - Security findings
  - `/api/v1/reliability/*` - Health monitoring
  - `/api/v1/recommendations/*` - Optimization suggestions
  - `/api/v1/automation/*` - Remediation actions
  - `/ws` - WebSocket for real-time updates

### 3. Core Services

#### Cost Optimization Service
**Components:**
- **Data Collector**: Fetches cost data from AWS Cost Explorer
- **Waste Analyzer**: Identifies idle, orphaned, and oversized resources
- **Forecaster**: ML-based spending prediction using Prophet
- **RI/SP Optimizer**: Reserved Instance and Savings Plan recommendations

**Key Algorithms:**
```python
# Idle Resource Detection
if avg_cpu < 5% AND duration > 7_days:
    classify_as_idle()

# Oversized Resource Detection  
if avg_cpu < 20% AND max_cpu < 50% AND duration > 14_days:
    recommend_downsize(current_size - 1)

# RI Recommendation
if running_hours > 730 * 0.75:  # 75% of month
    calculate_ri_savings()
```

**Data Models:**
- `CostData`: Daily spend by service/resource
- `WasteDetection`: Identified waste with evidence
- `Recommendation`: Optimization suggestions
- `Forecast`: Predicted spending

#### Security Service
**Components:**
- **Scanner Engine**: Executes 100+ security checks
- **Compliance Mapper**: Maps findings to frameworks (CIS, PCI, HIPAA)
- **Vulnerability Database**: Known CVEs and exploits
- **Risk Scorer**: CVSS-like severity calculation

**Check Categories:**
1. IAM (Identity & Access Management)
2. Network Security
3. Data Protection
4. Logging & Monitoring
5. Compute Security
6. Storage Security
7. Database Security

**Data Models:**
- `SecurityFinding`: Individual security issue
- `ComplianceScore`: Framework compliance percentage
- `VulnerabilityAlert`: Critical security alerts

#### Reliability Service
**Components:**
- **Health Monitor**: Real-time resource health checks
- **Limit Tracker**: AWS service limit utilization
- **Predictor**: Time-series forecasting for capacity planning
- **Architecture Analyzer**: Well-Architected Framework scoring

**Monitoring:**
- EC2: Status checks, disk space, CPU credits
- RDS: Replica lag, connections, storage
- ELB: Target health, request count
- S3: Bucket size, request errors
- Lambda: Throttles, errors, duration

**Data Models:**
- `HealthStatus`: Real-time health metrics
- `ServiceLimit`: Current usage vs. limit
- `Prediction`: Future capacity needs
- `ArchitectureScore`: Best practices compliance

#### Automation Service
**Components:**
- **Remediation Engine**: Executes approved actions
- **Workflow Manager**: Multi-step automation orchestration
- **Approval System**: Human-in-the-loop for risky actions
- **Rollback Manager**: Undo capability for all actions

**Safety Tiers:**
- **Tier 1 (Auto)**: No human approval needed
  - Enable encryption
  - Rotate old keys
  - Delete unattached volumes
- **Tier 2 (Approval)**: Requires approval
  - Stop/start instances
  - Modify security groups
  - Delete snapshots
- **Tier 3 (Manual)**: No automation
  - Production database changes
  - VPC modifications

**Data Models:**
- `AutomationRule`: Configured automation policies
- `ExecutionLog`: Audit trail of all actions
- `ApprovalRequest`: Pending human decisions
- `Rollback`: Stored state for undo operations

### 4. Data Layer

#### PostgreSQL (Primary Database)
**Schema Design:**

```sql
-- Accounts
CREATE TABLE accounts (
    id UUID PRIMARY KEY,
    customer_id UUID NOT NULL,
    aws_account_id VARCHAR(12) NOT NULL,
    name VARCHAR(255),
    role_arn TEXT NOT NULL,
    status VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW(),
    last_scan_at TIMESTAMP
);

-- Resources
CREATE TABLE resources (
    id UUID PRIMARY KEY,
    account_id UUID REFERENCES accounts(id),
    resource_id VARCHAR(255) NOT NULL,
    resource_type VARCHAR(50),
    region VARCHAR(50),
    metadata JSONB,
    tags JSONB,
    discovered_at TIMESTAMP DEFAULT NOW(),
    last_seen_at TIMESTAMP DEFAULT NOW()
);

-- Cost Data (TimescaleDB hypertable)
CREATE TABLE cost_data (
    time TIMESTAMP NOT NULL,
    account_id UUID REFERENCES accounts(id),
    service VARCHAR(100),
    resource_id VARCHAR(255),
    cost DECIMAL(10, 2),
    usage_amount DECIMAL(15, 4),
    usage_unit VARCHAR(50)
);
SELECT create_hypertable('cost_data', 'time');

-- Security Findings
CREATE TABLE security_findings (
    id UUID PRIMARY KEY,
    account_id UUID REFERENCES accounts(id),
    resource_id VARCHAR(255),
    check_id VARCHAR(100),
    severity VARCHAR(20),
    title TEXT,
    description TEXT,
    remediation TEXT,
    evidence JSONB,
    status VARCHAR(20),
    detected_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP
);

-- Recommendations
CREATE TABLE recommendations (
    id UUID PRIMARY KEY,
    account_id UUID REFERENCES accounts(id),
    resource_id VARCHAR(255),
    type VARCHAR(50),
    priority VARCHAR(20),
    title TEXT,
    description TEXT,
    potential_savings DECIMAL(10, 2),
    actions JSONB,
    status VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Automation Logs
CREATE TABLE automation_logs (
    id UUID PRIMARY KEY,
    recommendation_id UUID REFERENCES recommendations(id),
    action_type VARCHAR(50),
    status VARCHAR(20),
    executed_by UUID,
    executed_at TIMESTAMP,
    result JSONB,
    rollback_data JSONB
);
```

#### Redis (Cache & Session Store)
**Usage:**
- Session storage (JWT tokens)
- API response caching (TTL: 5-60 minutes)
- Rate limiting counters
- Real-time metrics aggregation
- WebSocket connection management

**Key Patterns:**
```
session:{user_id} → Session data
cache:cost:{account_id}:{date_range} → Cached cost data
cache:security:{account_id} → Cached findings
ratelimit:{user_id}:{endpoint} → Request counter
ws:connections:{account_id} → Active WebSocket clients
```

#### RabbitMQ (Message Queue)
**Queues:**
- `data_collection` - Periodic AWS data fetching
- `security_scans` - Security check execution
- `cost_analysis` - Cost calculations
- `automation_tasks` - Remediation actions
- `notifications` - Email/Slack alerts

**Exchange Types:**
- Direct: For specific routing
- Topic: For pattern-based routing
- Fanout: For broadcasting events

### 5. Background Workers

**Celery Workers**
**Job Types:**

1. **Scheduled Jobs** (Celery Beat)
   - Hourly: Resource health checks
   - Daily: Cost data collection, security scans
   - Weekly: Trend analysis, forecasting
   - Monthly: Compliance reports

2. **On-Demand Jobs**
   - New account onboarding
   - Manual security scans
   - Remediation execution
   - Report generation

3. **Event-Driven Jobs**
   - CloudWatch event processing
   - Cost anomaly alerts
   - Security incident response

**Worker Pools:**
- General pool (10 workers)
- Heavy tasks pool (5 workers, for scans)
- Priority pool (3 workers, for critical alerts)

### 6. External Integrations

#### AWS Services
**Authentication:**
- Cross-account IAM roles (AssumeRole)
- No access keys stored
- Session tokens with expiration

**APIs Used:**
- **Cost Explorer**: Cost and usage data
- **EC2**: Instance metadata, utilization
- **RDS**: Database metrics, snapshots
- **S3**: Bucket policies, encryption
- **IAM**: Users, roles, policies
- **CloudWatch**: Metrics, logs, alarms
- **Config**: Resource compliance
- **CloudTrail**: Audit logs
- **Trusted Advisor**: AWS recommendations

#### Third-Party Integrations
- **Slack**: Notifications and alerts
- **PagerDuty**: Incident management
- **Jira**: Ticket creation for findings
- **DataDog**: External monitoring
- **Stripe**: Payment processing

## Security Architecture

### Authentication & Authorization

**JWT-Based Auth:**
```
User Login → Generate JWT (access + refresh) → Store in Redis
API Request → Validate JWT → Check permissions → Allow/Deny
```

**RBAC (Role-Based Access Control):**
- **Admin**: Full access to all features
- **Analyst**: Read-only access + execute approved actions
- **Viewer**: Read-only access to dashboards

### Data Security

**Encryption:**
- **At Rest**: 
  - PostgreSQL: Transparent Data Encryption (TDE)
  - S3: SSE-S3 or SSE-KMS
  - RDS: Encryption enabled
- **In Transit**: 
  - TLS 1.3 for all API calls
  - WSS for WebSocket connections

**Secrets Management:**
- AWS Secrets Manager for database credentials
- AWS Systems Manager Parameter Store for configuration
- Never store secrets in code or environment variables

**Network Security:**
- VPC with private subnets for databases
- Security groups with least privilege
- WAF (Web Application Firewall) on ALB
- DDoS protection via AWS Shield

### Compliance

**SOC2 Requirements:**
- Audit logging for all actions
- Data retention policies
- Access controls and MFA
- Incident response procedures
- Regular security assessments

**GDPR Compliance:**
- Data encryption
- Right to deletion
- Data portability
- Consent management
- Privacy by design

## Scalability & Performance

### Horizontal Scaling

**Application Tier:**
- API Gateway: Auto-scaling group (2-20 instances)
- Workers: Kubernetes HPA (5-50 pods)
- Target: Handle 1000 concurrent users

**Data Tier:**
- PostgreSQL: Read replicas (3+)
- Redis: Cluster mode with 3+ nodes
- RabbitMQ: Clustered (3 nodes)

### Caching Strategy

**Multi-Layer Caching:**
1. **Browser**: Cache static assets (24h)
2. **CDN**: CloudFront caching (1h)
3. **API**: Redis caching (5-60m)
4. **Database**: Query result caching

**Cache Invalidation:**
- Time-based (TTL)
- Event-based (on data updates)
- Manual invalidation endpoint

### Performance Targets

| Metric | Target |
|--------|--------|
| API Response Time (p95) | <500ms |
| Dashboard Load Time | <2s |
| Real-time Update Latency | <100ms |
| Data Collection Cycle | <1h |
| Security Scan Duration | <5min per account |
| Database Query Time (p95) | <100ms |

## Disaster Recovery

### Backup Strategy

**Databases:**
- PostgreSQL: Automated daily backups (35-day retention)
- Point-in-time recovery (PITR) enabled
- Cross-region backup replication

**Configuration:**
- Infrastructure as Code (Terraform) in Git
- Secrets in AWS Secrets Manager (replicated)
- Application config in Parameter Store

### High Availability

**Architecture:**
- Multi-AZ deployment for all services
- Auto-scaling for compute
- Read replicas for databases
- Route 53 health checks with failover

**RTO/RPO:**
- Recovery Time Objective (RTO): <1 hour
- Recovery Point Objective (RPO): <15 minutes

## Monitoring & Observability

### Metrics (Prometheus + Grafana)

**Application Metrics:**
- Request rate, latency, error rate
- Active users and sessions
- Background job success/failure rate
- Cache hit/miss ratio

**Infrastructure Metrics:**
- CPU, memory, disk utilization
- Network throughput
- Database connections
- Queue depth

**Business Metrics:**
- Total savings identified
- Security findings count
- Automation execution rate
- Customer engagement

### Logging (CloudWatch)

**Log Levels:**
- ERROR: All errors and exceptions
- WARN: Unusual but handled situations
- INFO: Significant business events
- DEBUG: Detailed diagnostic information

**Structured Logging:**
```json
{
  "timestamp": "2026-01-03T12:00:00Z",
  "level": "INFO",
  "service": "cost-analyzer",
  "user_id": "user_123",
  "account_id": "aws_456",
  "action": "cost_analysis_completed",
  "duration_ms": 1234,
  "savings_found": 5000.00
}
```

### Alerting (PagerDuty)

**Alert Categories:**
- **P1 (Critical)**: System down, data breach
- **P2 (High)**: Degraded performance, partial outage
- **P3 (Medium)**: Non-critical errors, capacity warnings
- **P4 (Low)**: Informational, metrics drift

### Distributed Tracing (Jaeger)

**Trace spans:**
- API request → Service calls → Database queries → AWS API calls
- Full request lifecycle visibility
- Performance bottleneck identification

## Deployment

### CI/CD Pipeline (GitHub Actions)

```yaml
Stages:
1. Test:
   - Unit tests (pytest)
   - Integration tests
   - Security scanning (Snyk)
   - Code quality (SonarQube)

2. Build:
   - Docker image build
   - Tag with git SHA
   - Push to ECR

3. Deploy Staging:
   - Deploy to staging environment
   - Run smoke tests
   - Load testing

4. Deploy Production:
   - Blue-green deployment
   - Health check validation
   - Automatic rollback on failure
```

### Infrastructure as Code (Terraform)

**Modules:**
- `networking` - VPC, subnets, security groups
- `compute` - ECS/EKS, EC2, ALB
- `data` - RDS, ElastiCache, S3
- `monitoring` - CloudWatch, Prometheus
- `security` - IAM roles, KMS keys, Secrets Manager

### Environments

1. **Development**: Single instance, minimal resources
2. **Staging**: Production-like, for testing
3. **Production**: Multi-AZ, auto-scaling, fully monitored

## Cost Optimization (Eating Our Own Dog Food)

**Our AWS Spend Strategy:**
- Use Spot Instances for workers (save 70%)
- Reserved Instances for databases (save 40%)
- S3 Intelligent-Tiering for backups
- CloudFront caching to reduce origin load
- Auto-scaling to match demand

**Expected Monthly Cost:**
- Compute: $500-$2000
- Database: $300-$1000
- Storage: $100-$500
- Networking: $200-$800
- **Total**: $1100-$4300/month

**Cost per Customer:**
- At 10 customers: $110-$430/customer
- At 100 customers: $11-$43/customer
- At 1000 customers: $1.10-$4.30/customer

Gross margins improve significantly with scale!

## Future Enhancements

### Phase 2 (Months 6-12)
- GraphQL API for flexible queries
- Machine learning for custom anomaly detection
- Multi-account organization support
- Advanced RBAC with custom policies

### Phase 3 (Year 2)
- Multi-cloud support (Azure, GCP)
- Kubernetes cost optimization
- Carbon footprint tracking
- API marketplace for extensions

## Technical Decisions & Rationale

### Why FastAPI?
- ✅ High performance (async/await)
- ✅ Automatic API documentation (OpenAPI)
- ✅ Type safety with Pydantic
- ✅ Modern Python features

### Why PostgreSQL + TimescaleDB?
- ✅ ACID compliance for critical data
- ✅ Time-series optimization for metrics
- ✅ JSON support for flexible schema
- ✅ Mature ecosystem

### Why React?
- ✅ Large ecosystem and community
- ✅ Component reusability
- ✅ Excellent developer experience
- ✅ Strong TypeScript support

### Why Celery?
- ✅ Proven at scale
- ✅ Rich feature set (scheduling, retries, etc.)
- ✅ Python-native
- ✅ Monitoring tools (Flower)

## Conclusion

This architecture is designed for:
- **Scalability**: Handle 1000+ customers
- **Reliability**: 99.9% uptime SLA
- **Security**: SOC2 and GDPR compliant
- **Performance**: Sub-second response times
- **Cost-Efficiency**: Profitable at scale

The modular design allows for incremental development and easy testing of individual components.
