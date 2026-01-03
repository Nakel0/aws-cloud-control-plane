# CloudGuard - Unified AWS Cloud Optimization Platform

<p align="center">
  <img src="https://img.shields.io/badge/AWS-Supported-FF9900?logo=amazonaws" alt="AWS">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/React-18-61DAFB?logo=react" alt="React">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License">
</p>

**CloudGuard** is an intelligent cloud optimization platform that helps companies **reduce cloud waste, prevent security misconfigurations, and improve system reliability**—automatically.

## 🎯 Key Value Propositions

| Problem | CloudGuard Solution | Impact |
|---------|-------------------|--------|
| 💰 **Cloud Waste** | Detects idle, oversized, and unattached resources | Save 20-35% on cloud spend |
| 🔒 **Security Risks** | Finds public buckets, open ports, missing encryption | Prevent data breaches |
| ⚡ **Reliability Gaps** | Identifies single-AZ, no backups, missing monitoring | Improve uptime to 99.99% |

## 🚀 Features

### Cost Optimization
- **Idle Resource Detection** - Find EC2, RDS, ELB with low utilization
- **Rightsizing Recommendations** - Downsize oversized instances
- **Orphaned Resource Cleanup** - Unattached EBS, unused EIPs
- **Reserved Instance Analysis** - RI/Savings Plan opportunities
- **Cost Anomaly Detection** - Unusual spend alerts

### Security Scanning
- **Public Access Detection** - S3 buckets, security groups, RDS
- **Encryption Audit** - EBS, RDS, S3 encryption status
- **IAM Security** - Unused credentials, overly permissive policies
- **Root Account Security** - MFA and access key checks
- **Compliance Mapping** - CIS AWS, SOC2, PCI-DSS, HIPAA

### Reliability Analysis
- **High Availability Gaps** - Single-AZ deployments
- **Backup Coverage** - RDS, EBS snapshot status
- **Auto-Recovery** - Auto Scaling coverage
- **Monitoring Gaps** - CloudWatch alarm coverage
- **Health Check Optimization** - ELB health check tuning

### Automation
- **One-Click Remediation** - Fix issues automatically
- **Dry-Run Mode** - Preview changes before applying
- **Rollback Support** - Undo actions when needed
- **Scheduled Scans** - Continuous monitoring

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     CloudGuard Platform                      │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │   React     │  │   FastAPI   │  │   Celery    │          │
│  │  Dashboard  │──│   Backend   │──│   Workers   │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
│         │               │               │                    │
│         └───────────────┼───────────────┘                    │
│                         │                                    │
│  ┌─────────────────────┴─────────────────────┐              │
│  │              AWS Integration              │              │
│  │  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ │              │
│  │  │ EC2 │ │ RDS │ │ S3  │ │ IAM │ │ CW  │ │              │
│  │  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ │              │
│  └───────────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────┘
```

## 📦 Installation

### Prerequisites
- Python 3.11+
- Node.js 18+
- AWS Account with appropriate permissions
- PostgreSQL (optional, for persistence)
- Redis (optional, for background tasks)

### Quick Start

1. **Clone the repository**
```bash
git clone https://github.com/yourorg/cloudguard.git
cd cloudguard
```

2. **Set up the backend**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
```

3. **Configure AWS credentials**
```bash
# Option 1: Environment variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=us-east-1

# Option 2: Create .env file
cp .env.example .env
# Edit .env with your credentials
```

4. **Start the backend**
```bash
uvicorn app.main:app --reload
```

5. **Set up the frontend**
```bash
cd ../frontend
npm install
npm run dev
```

6. **Access the dashboard**
Open http://localhost:3000 in your browser.

## ⚙️ Configuration

### Environment Variables

```env
# Application
APP_NAME=CloudGuard
DEBUG=false
ENVIRONMENT=production

# AWS
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=us-east-1
AWS_ASSUME_ROLE_ARN=  # Optional: for cross-account access

# Database (optional)
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/cloudguard

# Redis (optional)
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-super-secret-key

# Scanning
SCAN_INTERVAL_HOURS=6
LOW_UTILIZATION_THRESHOLD=10.0
```

### Required AWS Permissions

Create an IAM policy with these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:Describe*",
        "rds:Describe*",
        "s3:GetBucket*",
        "s3:ListAllMyBuckets",
        "iam:Get*",
        "iam:List*",
        "cloudwatch:GetMetricStatistics",
        "cloudwatch:DescribeAlarms",
        "ce:GetCostAndUsage",
        "ce:GetReservationPurchaseRecommendation",
        "elasticloadbalancing:Describe*",
        "autoscaling:Describe*",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

For remediation capabilities, add write permissions as needed.

## 📊 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/dashboard` | GET | Complete dashboard summary |
| `/api/v1/cost/summary` | GET | Cost optimization summary |
| `/api/v1/security/summary` | GET | Security posture summary |
| `/api/v1/reliability/summary` | GET | Reliability summary |
| `/api/v1/findings` | GET | List all findings |
| `/api/v1/scans` | POST | Start new scan |
| `/api/v1/remediate/{id}` | POST | Execute remediation |

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest tests/ -v --cov=app

# Frontend tests
cd frontend
npm test
```

## 🚢 Deployment

### Docker

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d
```

### AWS Deployment (Recommended)

1. Deploy backend to **AWS Lambda** or **ECS Fargate**
2. Deploy frontend to **S3 + CloudFront**
3. Use **RDS PostgreSQL** for database
4. Use **ElastiCache Redis** for caching
5. Configure **EventBridge** for scheduled scans

## 📈 Roadmap

- [x] AWS Support
- [ ] Azure Support
- [ ] GCP Support
- [ ] Multi-cloud Dashboard
- [ ] Terraform Integration
- [ ] Slack/Teams Notifications
- [ ] Custom Rule Engine
- [ ] ML-based Anomaly Detection

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md).

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

<p align="center">
  Built with ❤️ for the cloud-native community
</p>
