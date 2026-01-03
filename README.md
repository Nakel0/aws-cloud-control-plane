# Unified Cloud Platform (AWS)

## Overview
A unified platform to reduce cloud waste, enforce security, and improve reliability on AWS.

## Is this Sellable?
**Yes.** This operates in the high-demand sectors of FinOps (Cost), CSPM (Security), and CloudOps.
- **Value Proposition:** "One dashboard to save money and sleep better."
- **Market:** Any company using AWS (Startups to Enterprise).
- **Competitors:** Wiz, CloudHealth, Datadog (High end); Vantage, CloudCustodia (Niche/Open Source).
- **Strategy:** Start with specific, high-impact automations (e.g., "One-click delete unattached EBS volumes") to differentiate.

## Step-by-Step Implementation Guide

### Phase 1: Foundation & Connectivity (Current Focus)
1. **Tech Stack Selection:**
   - **Backend:** Python (FastAPI) + Boto3 (Best for AWS automation).
   - **Frontend:** React / Next.js (Dashboard).
   - **Database:** PostgreSQL (Store inventory and findings).
2. **AWS Connectivity:**
   - **Mechanism:** Cross-Account IAM Roles (Secure, no access keys shared).
   - **User Flow:** User runs a CloudFormation template in their AWS account -> Creates Role -> Grants your platform permission.

### Phase 2: The Scanner Engine
Build modular "Scanners" for different domains:
1. **Cost Scanner:**
   - Find idle EC2 instances (CPU < 5% for 7 days).
   - Find unattached EBS volumes.
   - Find unallocated Elastic IPs.
2. **Security Scanner:**
   - Check Security Groups for `0.0.0.0/0` on port 22/3389.
   - Check S3 buckets for public access.
   - Check if MFA is enabled for root.
3. **Reliability Scanner:**
   - Check if RDS Multi-AZ is enabled for production tags.
   - Check for recent backups.

### Phase 3: The Dashboard & Reporting
- Display "Potential Monthly Savings" ($).
- Display "Security Score" (A-F).
- List specific actionable findings.

### Phase 4: Remediation (The "Auto" in Automation)
- **Manual Approval:** User clicks "Fix" -> Platform executes API call to fix.
- **Auto-Fix:** (Advanced) Policy-based automatic cleanup.

## Getting Started
See `backend/README.md` to start the API.
