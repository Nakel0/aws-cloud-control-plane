# Technical Architecture: Unified Cloud Platform

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                       │
│  - Dashboard UI                                             │
│  - Real-time updates (WebSocket)                            │
│  - Authentication (Auth0/Clerk)                             │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTPS/WSS
┌──────────────────────▼──────────────────────────────────────┐
│                 API Gateway (AWS API Gateway)               │
│  - Rate limiting                                             │
│  - Authentication middleware                                 │
│  - Request routing                                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│              Backend Services (ECS Fargate)                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Cost       │  │   Security   │  │ Reliability  │     │
│  │   Service    │  │   Service    │  │   Service    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Auth       │  │   Notification│  │   Analytics  │     │
│  │   Service    │  │   Service    │  │   Service    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│            Data Collection Layer (Lambda Functions)          │
│  - Cost data collector (scheduled)                          │
│  - Security scanner (scheduled + event-driven)              │
│  - Metrics collector (CloudWatch → our DB)                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                    Message Queue (SQS)                       │
│  - Job queue for async processing                           │
│  - Dead letter queue for failed jobs                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│              Processing Workers (ECS Tasks)                  │
│  - Recommendation engine                                    │
│  - Risk scoring                                             │
│  - Alert generation                                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                    Data Storage                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ PostgreSQL   │  │  TimescaleDB │  │    Redis     │     │
│  │ (Metadata)   │  │  (Metrics)   │  │   (Cache)   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│              AWS Services Integration                        │
│  - Cost Explorer API                                        │
│  - Config API                                               │
│  - Security Hub API                                         │
│  - CloudWatch API                                           │
│  - IAM API                                                  │
└─────────────────────────────────────────────────────────────┘
```

## Technology Stack

### Frontend
- **Framework**: Next.js 14+ (React)
- **Language**: TypeScript
- **UI Library**: Tailwind CSS + shadcn/ui
- **State Management**: Zustand or React Query
- **Charts**: Recharts or Chart.js
- **Real-time**: WebSocket (Socket.io)

### Backend
- **Language**: Python 3.11+ (FastAPI) OR Node.js 20+ (NestJS)
- **Framework**: FastAPI (Python) or NestJS (Node.js)
- **API Style**: REST + GraphQL (optional)
- **Authentication**: JWT tokens
- **Validation**: Pydantic (Python) or class-validator (Node.js)

### Database
- **Primary DB**: PostgreSQL 15+ (RDS)
- **Time-Series**: TimescaleDB (for metrics)
- **Cache**: Redis (ElastiCache)
- **Search**: Elasticsearch (optional, for advanced search)

### Infrastructure (AWS)
- **Compute**: ECS Fargate (containers)
- **Serverless**: AWS Lambda (data collection)
- **API Gateway**: AWS API Gateway
- **Queue**: AWS SQS
- **Storage**: S3 (file storage, backups)
- **CDN**: CloudFront
- **Monitoring**: CloudWatch + Datadog/New Relic

### DevOps
- **CI/CD**: GitHub Actions or GitLab CI
- **Infrastructure as Code**: Terraform
- **Container Registry**: ECR
- **Secrets**: AWS Secrets Manager
- **Logging**: CloudWatch Logs

## Database Schema

### Core Tables

```sql
-- Users and Organizations
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    plan VARCHAR(50) NOT NULL DEFAULT 'starter',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'member',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- AWS Accounts
CREATE TABLE aws_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    account_id VARCHAR(12) NOT NULL,
    account_name VARCHAR(255),
    access_key_id VARCHAR(255) NOT NULL, -- Encrypted
    secret_access_key VARCHAR(255) NOT NULL, -- Encrypted
    region VARCHAR(50) DEFAULT 'us-east-1',
    is_active BOOLEAN DEFAULT TRUE,
    last_sync_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(organization_id, account_id)
);

-- Cost Data
CREATE TABLE cost_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID REFERENCES aws_accounts(id),
    service VARCHAR(100),
    amount DECIMAL(12,2),
    currency VARCHAR(3) DEFAULT 'USD',
    date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_account_date (account_id, date)
);

-- Cost Recommendations
CREATE TABLE cost_recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID REFERENCES aws_accounts(id),
    resource_type VARCHAR(50) NOT NULL,
    resource_id VARCHAR(255) NOT NULL,
    recommendation_type VARCHAR(50) NOT NULL, -- 'idle', 'rightsize', 'reserved_instance'
    current_cost DECIMAL(10,2),
    potential_savings DECIMAL(10,2),
    description TEXT,
    action_required TEXT,
    status VARCHAR(20) DEFAULT 'open', -- 'open', 'applied', 'dismissed'
    priority VARCHAR(20) DEFAULT 'medium', -- 'low', 'medium', 'high', 'critical'
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_account_status (account_id, status)
);

-- Security Findings
CREATE TABLE security_findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID REFERENCES aws_accounts(id),
    resource_type VARCHAR(50),
    resource_id VARCHAR(255),
    finding_type VARCHAR(100) NOT NULL, -- 'public_s3_bucket', 'overly_permissive_iam', etc.
    severity VARCHAR(20) NOT NULL, -- 'critical', 'high', 'medium', 'low', 'info'
    title VARCHAR(255) NOT NULL,
    description TEXT,
    remediation_steps TEXT,
    compliance_frameworks TEXT[], -- ['CIS', 'SOC2', 'PCI-DSS']
    status VARCHAR(20) DEFAULT 'open', -- 'open', 'resolved', 'suppressed'
    detected_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_account_severity (account_id, severity),
    INDEX idx_account_status (account_id, status)
);

-- Reliability Metrics
CREATE TABLE reliability_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID REFERENCES aws_accounts(id),
    service_name VARCHAR(100),
    metric_name VARCHAR(100),
    value DECIMAL(10,2),
    unit VARCHAR(50),
    timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
) PARTITION BY RANGE (timestamp);

-- Alerts
CREATE TABLE alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID REFERENCES aws_accounts(id),
    alert_type VARCHAR(50) NOT NULL, -- 'cost_anomaly', 'security_finding', 'reliability_issue'
    severity VARCHAR(20) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT,
    resource_type VARCHAR(50),
    resource_id VARCHAR(255),
    status VARCHAR(20) DEFAULT 'active', -- 'active', 'acknowledged', 'resolved'
    created_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP,
    INDEX idx_account_status (account_id, status)
);

-- Actions (Automated Remediations)
CREATE TABLE actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID REFERENCES aws_accounts(id),
    action_type VARCHAR(50) NOT NULL, -- 'stop_instance', 'delete_snapshot', 'fix_s3_permissions'
    resource_type VARCHAR(50),
    resource_id VARCHAR(255),
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'approved', 'executed', 'failed'
    executed_at TIMESTAMP,
    result JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_account_status (account_id, status)
);
```

### TimescaleDB Tables (for metrics)

```sql
-- Create hypertable for time-series data
CREATE TABLE metrics (
    time TIMESTAMPTZ NOT NULL,
    account_id UUID NOT NULL,
    service VARCHAR(100),
    metric_name VARCHAR(100),
    value DOUBLE PRECISION,
    tags JSONB
);

SELECT create_hypertable('metrics', 'time');
```

## API Design

### REST API Endpoints

#### Authentication
```
POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh
POST   /api/v1/auth/logout
```

#### AWS Accounts
```
GET    /api/v1/accounts
POST   /api/v1/accounts
GET    /api/v1/accounts/{id}
PUT    /api/v1/accounts/{id}
DELETE /api/v1/accounts/{id}
POST   /api/v1/accounts/{id}/sync
```

#### Cost Optimization
```
GET    /api/v1/cost/summary
GET    /api/v1/cost/trends
GET    /api/v1/cost/recommendations
POST   /api/v1/cost/recommendations/{id}/apply
POST   /api/v1/cost/recommendations/{id}/dismiss
GET    /api/v1/cost/budgets
POST   /api/v1/cost/budgets
```

#### Security
```
GET    /api/v1/security/findings
GET    /api/v1/security/findings/{id}
POST   /api/v1/security/findings/{id}/resolve
GET    /api/v1/security/compliance
GET    /api/v1/security/score
```

#### Reliability
```
GET    /api/v1/reliability/health
GET    /api/v1/reliability/metrics
GET    /api/v1/reliability/alerts
POST   /api/v1/reliability/alerts/{id}/acknowledge
```

#### Actions
```
GET    /api/v1/actions
POST   /api/v1/actions
GET    /api/v1/actions/{id}
POST   /api/v1/actions/{id}/approve
POST   /api/v1/actions/{id}/execute
```

### Example API Response

```json
{
  "cost": {
    "summary": {
      "current_month": 12500.50,
      "last_month": 11800.25,
      "change_percent": 5.9,
      "potential_savings": 2500.00,
      "savings_percent": 20.0
    },
    "recommendations": [
      {
        "id": "uuid",
        "type": "idle_instance",
        "resource_type": "ec2",
        "resource_id": "i-1234567890abcdef0",
        "current_cost": 150.00,
        "potential_savings": 150.00,
        "description": "EC2 instance has been idle for 14 days",
        "action_required": "Stop or terminate instance",
        "priority": "high"
      }
    ]
  },
  "security": {
    "score": 72,
    "findings": {
      "critical": 2,
      "high": 5,
      "medium": 12,
      "low": 8
    },
    "compliance": {
      "CIS": 85,
      "SOC2": 78,
      "PCI-DSS": 65
    }
  },
  "reliability": {
    "score": 98.5,
    "uptime_30d": 99.9,
    "active_alerts": 3,
    "services_healthy": 45,
    "services_degraded": 2,
    "services_down": 0
  }
}
```

## Data Collection Strategy

### Cost Data Collection

```python
# cost_collector.py
import boto3
from datetime import datetime, timedelta
from decimal import Decimal

class CostCollector:
    def __init__(self, aws_account):
        self.ce_client = boto3.client('ce',
            aws_access_key_id=aws_account.access_key_id,
            aws_secret_access_key=aws_account.secret_access_key,
            region_name='us-east-1'
        )
    
    def collect_daily_costs(self, start_date, end_date):
        """Collect cost data from AWS Cost Explorer"""
        response = self.ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': start_date.strftime('%Y-%m-%d'),
                'End': end_date.strftime('%Y-%m-%d')
            },
            Granularity='DAILY',
            Metrics=['BlendedCost', 'UnblendedCost'],
            GroupBy=[
                {'Type': 'DIMENSION', 'Key': 'SERVICE'},
                {'Type': 'DIMENSION', 'Key': 'USAGE_TYPE'}
            ]
        )
        return response
    
    def find_idle_resources(self):
        """Identify idle EC2 instances"""
        ec2_client = boto3.client('ec2',
            aws_access_key_id=self.aws_account.access_key_id,
            aws_secret_access_key=self.aws_account.secret_access_key
        )
        cloudwatch = boto3.client('cloudwatch',
            aws_access_key_id=self.aws_account.access_key_id,
            aws_secret_access_key=self.aws_account.secret_access_key
        )
        
        # Get all running instances
        instances = ec2_client.describe_instances(
            Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
        )
        
        idle_instances = []
        for reservation in instances['Reservations']:
            for instance in reservation['Instances']:
                instance_id = instance['InstanceId']
                
                # Check CPU utilization for last 7 days
                cpu_metrics = cloudwatch.get_metric_statistics(
                    Namespace='AWS/EC2',
                    MetricName='CPUUtilization',
                    Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                    StartTime=datetime.now() - timedelta(days=7),
                    EndTime=datetime.now(),
                    Period=3600,
                    Statistics=['Average']
                )
                
                avg_cpu = sum(
                    point['Average'] for point in cpu_metrics['Datapoints']
                ) / len(cpu_metrics['Datapoints']) if cpu_metrics['Datapoints'] else 0
                
                if avg_cpu < 5.0:  # Less than 5% CPU
                    idle_instances.append({
                        'instance_id': instance_id,
                        'avg_cpu': avg_cpu,
                        'instance_type': instance['InstanceType']
                    })
        
        return idle_instances
```

### Security Scanning

```python
# security_scanner.py
import boto3

class SecurityScanner:
    def __init__(self, aws_account):
        self.config_client = boto3.client('config',
            aws_access_key_id=aws_account.access_key_id,
            aws_secret_access_key=aws_account.secret_access_key
        )
        self.s3_client = boto3.client('s3',
            aws_access_key_id=aws_account.access_key_id,
            aws_secret_access_key=aws_account.secret_access_key
        )
        self.iam_client = boto3.client('iam',
            aws_access_key_id=aws_account.access_key_id,
            aws_secret_access_key=aws_account.secret_access_key
        )
    
    def scan_public_s3_buckets(self):
        """Find publicly accessible S3 buckets"""
        findings = []
        buckets = self.s3_client.list_buckets()
        
        for bucket in buckets['Buckets']:
            bucket_name = bucket['Name']
            try:
                acl = self.s3_client.get_bucket_acl(Bucket=bucket_name)
                policy = self.s3_client.get_bucket_policy(Bucket=bucket_name)
                
                # Check if bucket is public
                is_public = False
                for grant in acl.get('Grants', []):
                    grantee = grant.get('Grantee', {})
                    if grantee.get('Type') == 'Group' and 'AllUsers' in grantee.get('URI', ''):
                        is_public = True
                        break
                
                if is_public:
                    findings.append({
                        'resource_type': 's3_bucket',
                        'resource_id': bucket_name,
                        'finding_type': 'public_s3_bucket',
                        'severity': 'high',
                        'description': f'S3 bucket {bucket_name} is publicly accessible',
                        'remediation_steps': 'Remove public access or add bucket policy restrictions'
                    })
            except Exception as e:
                # Bucket might not exist or no permission
                pass
        
        return findings
    
    def scan_overly_permissive_iam(self):
        """Find IAM policies with overly permissive access"""
        findings = []
        
        # Scan user policies
        users = self.iam_client.list_users()
        for user in users['Users']:
            policies = self.iam_client.list_user_policies(UserName=user['UserName'])
            attached_policies = self.iam_client.list_attached_user_policies(UserName=user['UserName'])
            
            # Check for wildcard permissions
            for policy_name in policies['PolicyNames']:
                policy_doc = self.iam_client.get_user_policy(
                    UserName=user['UserName'],
                    PolicyName=policy_name
                )
                
                if self._has_wildcard_permission(policy_doc['PolicyDocument']):
                    findings.append({
                        'resource_type': 'iam_user',
                        'resource_id': user['UserName'],
                        'finding_type': 'overly_permissive_iam',
                        'severity': 'critical',
                        'description': f'IAM user {user["UserName"]} has overly permissive policy',
                        'remediation_steps': 'Apply principle of least privilege'
                    })
        
        return findings
    
    def _has_wildcard_permission(self, policy_doc):
        """Check if policy has wildcard permissions"""
        for statement in policy_doc.get('Statement', []):
            if statement.get('Effect') == 'Allow':
                actions = statement.get('Action', [])
                resources = statement.get('Resource', [])
                
                if '*' in actions or '*' in resources:
                    return True
        return False
```

## Deployment Architecture

### Infrastructure as Code (Terraform)

```hcl
# main.tf
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# VPC
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support = true
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "cloud-platform-cluster"
}

# RDS PostgreSQL
resource "aws_db_instance" "main" {
  identifier = "cloud-platform-db"
  engine = "postgres"
  engine_version = "15.4"
  instance_class = "db.t3.medium"
  allocated_storage = 100
  db_name = "cloudplatform"
  username = var.db_username
  password = var.db_password
  
  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name = aws_db_subnet_group.main.name
}

# ECS Service
resource "aws_ecs_service" "api" {
  name = "api-service"
  cluster = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count = 2
  
  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name = "api"
    container_port = 8000
  }
}
```

## Security Considerations

1. **Encryption**
   - Encrypt AWS credentials at rest (AWS KMS)
   - TLS for all API communications
   - Encrypt database connections

2. **Access Control**
   - Role-based access control (RBAC)
   - API rate limiting
   - IP whitelisting (optional)

3. **Audit Logging**
   - Log all API requests
   - Track all actions taken
   - Compliance reporting

4. **Secrets Management**
   - Use AWS Secrets Manager
   - Never log credentials
   - Rotate credentials regularly

## Monitoring & Observability

1. **Application Monitoring**
   - CloudWatch Metrics
   - Custom business metrics
   - Error tracking (Sentry)

2. **Logging**
   - Centralized logging (CloudWatch Logs)
   - Structured logging (JSON)
   - Log retention policies

3. **Alerting**
   - Critical errors → PagerDuty
   - Cost anomalies → Email/Slack
   - Security findings → Immediate alerts

## Scalability Considerations

1. **Horizontal Scaling**
   - Stateless API services
   - Load balancer distribution
   - Auto-scaling groups

2. **Database Scaling**
   - Read replicas for queries
   - Connection pooling
   - Query optimization

3. **Caching**
   - Redis for frequently accessed data
   - CDN for static assets
   - API response caching

4. **Async Processing**
   - SQS for job queues
   - Background workers
   - Event-driven architecture
