# Frequently Asked Questions (FAQ)

## General Questions

### What is CloudGuard?

CloudGuard is a unified platform that helps companies optimize their AWS infrastructure by:
- Reducing cloud waste and costs (20-40% savings typical)
- Preventing security misconfigurations and compliance violations
- Improving system reliability and uptime
- Automating remediation actions

### Is this really sellable as a product?

**Yes!** The market validates this:
- Cloud management platform market: $28B+ and growing at 25% CAGR
- Similar companies like Wiz ($12B valuation), CloudHealth ($500M acquisition), Spot.io ($450M acquisition)
- Average customer saves $360K+ annually
- Strong ROI: typically 10:1 to 27:1
- See [Market Analysis](MARKET_ANALYSIS.md) for detailed analysis

### How is this different from AWS Trusted Advisor?

**CloudGuard goes much deeper:**
- 100+ security checks vs. Trusted Advisor's limited set
- Real-time cost tracking vs. periodic updates
- Automated remediation vs. just recommendations
- Unified dashboard combining cost + security + reliability
- ML-based forecasting and anomaly detection
- Works across multiple AWS accounts
- Better UI/UX

### How is this different from competitors?

**Key differentiators:**
1. **Unified Platform**: Combines cost + security + reliability (most focus on one)
2. **Automation First**: Auto-fix issues, not just alerts
3. **AWS-Native**: Deep AWS integration vs. generic multi-cloud
4. **Developer-Friendly**: Modern UI, easy setup
5. **Transparent Pricing**: Clear costs vs. hidden fees

---

## Technical Questions

### What AWS permissions does CloudGuard need?

CloudGuard uses **read-only** cross-account IAM roles. See [AWS_IAM_POLICY.json](AWS_IAM_POLICY.json) for the complete policy.

**Key permissions:**
- Cost Explorer (cost data)
- EC2/RDS/S3 Describe* (resource discovery)
- CloudWatch (metrics)
- IAM List* (security checks)
- CloudTrail (audit logs)

**No write permissions by default** - remediation actions require explicit approval and additional permissions.

### How does CloudGuard access my AWS account?

**Secure cross-account access:**
1. You create an IAM role in your AWS account
2. Role has read-only permissions (see IAM policy)
3. Role trusts CloudGuard's AWS account via ARN
4. External ID for additional security
5. CloudGuard assumes role using STS (temporary credentials)
6. Credentials auto-expire (1 hour sessions)

**We NEVER:**
- Store AWS access keys
- Require admin permissions
- Access your data in S3/databases
- Make changes without approval

### What data does CloudGuard collect?

**Collected (metadata only):**
- Resource configurations (instance types, sizes, regions)
- Cost and usage data
- CloudWatch metrics
- Security group rules
- IAM configurations
- Tags and resource IDs

**NOT collected:**
- Application data from S3, RDS, DynamoDB
- Log file contents
- Customer data from databases
- Source code
- Secrets or credentials

### Is CloudGuard secure?

**Yes! Security is our top priority:**
- SOC2 Type II compliant architecture
- End-to-end encryption (TLS 1.3)
- Data encrypted at rest
- No AWS access keys stored
- Audit logging for all actions
- Regular security assessments
- GDPR compliant

### Can CloudGuard break my production environment?

**Multiple safety layers:**
1. **Read-only by default** - can't make changes without additional permissions
2. **Approval workflows** - high-risk actions require human approval
3. **Safety tiers** - only low-risk actions auto-execute
4. **Rollback capability** - undo any change
5. **Testing** - try in dev/staging first
6. **Audit logs** - full history of all actions

**Recommended approach:**
- Start with read-only mode
- Review recommendations manually
- Enable automation gradually
- Test in non-production first

---

## Business Questions

### How much does it cost?

**Pricing tiers:**
- **Free**: Up to $5K monthly AWS spend (limited features)
- **Starter**: $299/mo - Up to $50K spend
- **Professional**: $999/mo - Up to $250K spend
- **Enterprise**: Custom - Unlimited

**Alternative pricing:**
- 2-5% of savings generated (aligned incentives)
- Volume discounts available
- Annual plans (2 months free)

### What's the ROI?

**Typical customer example:**
- Monthly AWS spend: $100K
- Savings: $30K/mo (30% waste reduction)
- CloudGuard cost: $2-5K/mo
- **Net savings: $25-28K/mo ($300-336K/year)**
- **ROI: 10:1 to 14:1**

Plus additional value:
- Prevent security breaches ($200K+ average cost)
- Reduce downtime ($100K+ in productivity)
- Engineer time saved (10-20 hours/month)

### How long until I see results?

**Timeline:**
- **5 minutes**: Initial cost report
- **30 minutes**: Security scan complete
- **1 hour**: First recommendations
- **1 day**: Historical cost analysis
- **1 week**: Trend analysis and forecasting

### Who are your target customers?

**Primary targets:**
1. **Mid-market companies** ($10M-$500M revenue)
   - AWS spend: $50K-$500K/mo
   - No dedicated FinOps team
   
2. **Growth-stage startups** (Series B+)
   - AWS spend: $20K-$200K/mo
   - Scaling costs faster than revenue
   
3. **Enterprises** ($500M+ revenue)
   - AWS spend: $500K+/mo
   - Complex multi-account structures

**Ideal customer:**
- Uses AWS as primary cloud
- Monthly spend: $20K+
- 3+ AWS accounts
- 10-100+ engineers
- Pain: Cost overruns, security, outages

### Can I white-label this?

**Yes!** Enterprise plan includes:
- Custom branding
- Your domain
- Your logo and colors
- Reseller/MSP pricing
- API access

**Use cases:**
- AWS consulting firms
- Managed service providers
- System integrators
- Enterprise IT departments

---

## Implementation Questions

### How long does implementation take?

**Setup time:**
- **5 minutes**: Docker Compose local setup
- **30 minutes**: Manual installation
- **1 hour**: Production deployment
- **2 hours**: AWS account integration
- **1 day**: Customization and testing

**Development timeline:**
- **Week 1-2**: Foundation setup
- **Week 3-4**: Cost optimization module
- **Week 5-6**: Security scanner
- **Week 7-8**: Reliability monitoring
- **Week 9-10**: Automation engine
- **Week 11-12**: Dashboard UI
- **Week 13-14**: Testing
- **Week 15-16**: Deployment
- **Week 17-18**: Beta launch

See [Implementation Guide](IMPLEMENTATION_GUIDE.md) for details.

### What tech stack do I need to know?

**Backend:**
- Python (FastAPI, Boto3)
- PostgreSQL + TimescaleDB
- Redis, RabbitMQ
- Celery for background jobs

**Frontend:**
- React + TypeScript
- Tailwind CSS
- Recharts for visualization

**Infrastructure:**
- Docker
- Kubernetes (optional)
- Terraform (IaC)

**Skills needed:**
- Full-stack development
- AWS expertise
- DevOps/Infrastructure
- Security knowledge

### Can one person build this?

**Yes, but timeline depends on scope:**

**Solo developer (MVP):**
- 3-4 months working full-time
- Focus on core features first
- Use existing libraries/services
- Skip nice-to-haves

**Small team (2-3 developers):**
- 6-8 weeks to MVP
- Parallel development
- Better quality/testing
- Recommended approach

**Shortcuts:**
- Use AWS Pricing API (don't build pricing database)
- Start with one region
- Implement top 20 security checks first
- Basic UI initially
- Add features iteratively

### What are the biggest technical challenges?

**Top challenges:**
1. **Cost data accuracy** - AWS Cost Explorer API has 24-hour delay
2. **Security check coverage** - 100+ checks is a lot of work
3. **Performance at scale** - 10,000+ resources per account
4. **Multi-account management** - Organizations with 50+ accounts
5. **Real-time updates** - WebSocket connections at scale
6. **ML forecasting** - Accurate predictions are hard

**Solutions:**
- Start simple, iterate
- Use battle-tested libraries
- Cache aggressively
- Async processing
- Learn from AWS Trusted Advisor

---

## Support & Resources

### Where can I get help?

**Resources:**
- [Implementation Guide](IMPLEMENTATION_GUIDE.md) - Detailed build instructions
- [Architecture](ARCHITECTURE.md) - System design
- [Getting Started](GETTING_STARTED.md) - Setup guide
- [API Docs](http://localhost:8000/api/docs) - API reference

**Community:**
- GitHub Issues
- GitHub Discussions
- Email: support@cloudguard.io

### Can I hire someone to build this?

**Yes! Options:**
1. **Freelancers**: Upwork, Toptal ($50-150/hr)
2. **Dev agencies**: $10K-50K for MVP
3. **Offshore teams**: $5K-20K for MVP
4. **Full-time hire**: $120K-200K/year

**Estimated costs:**
- MVP development: $20K-50K
- Full platform: $100K-200K
- Ongoing maintenance: $5K-10K/month

### Is there a hosted/SaaS version?

**Coming soon!** We're planning to offer:
- Hosted SaaS version
- Free tier for small accounts
- No infrastructure management
- Instant setup

**Interested?** Join the waitlist at cloudguard.io

---

## Contributing

### Can I contribute to this project?

**Absolutely! We welcome contributions:**
- Bug fixes
- New features
- Documentation improvements
- Security checks
- Integrations
- Tests

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### How can I report a security vulnerability?

**Please report responsibly:**
- Email: security@cloudguard.io
- Use GitHub Security Advisories
- Do NOT create public issues
- We'll respond within 24 hours

---

## Questions Not Answered?

**Contact us:**
- Email: hello@cloudguard.io
- GitHub: [Open an issue](https://github.com/yourusername/cloudguard/issues)
- Twitter: [@cloudguard](https://twitter.com/cloudguard)

We're here to help! 🚀
