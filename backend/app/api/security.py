"""
Security Scanning API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import Account, SecurityFinding, Severity, FindingStatus
from app.services.security_scanner import SecurityScanner
from app.services.aws_client import AWSClient

router = APIRouter()


class SecurityFindingResponse(BaseModel):
    """Security finding response model"""
    id: str
    account_id: str
    resource_id: str
    resource_type: str
    check_id: str
    check_name: str
    title: str
    description: str
    severity: str
    status: str
    remediation: Optional[str]
    evidence: dict
    compliance_frameworks: Optional[list]
    detected_at: str
    resolved_at: Optional[str]

    class Config:
        from_attributes = True


class SecuritySummaryResponse(BaseModel):
    """Security summary response"""
    account_id: str
    total_findings: int
    severity_breakdown: dict
    status_breakdown: dict
    compliance_scores: dict
    last_scan_at: Optional[str]


class ComplianceReportResponse(BaseModel):
    """Compliance report response"""
    framework: str
    total_controls: int
    passing_controls: int
    failing_controls: int
    compliance_percentage: float
    findings: List[dict]


@router.get("/{account_id}/findings", response_model=List[SecurityFindingResponse])
async def list_security_findings(
    account_id: UUID,
    severity: Optional[Severity] = Query(None, description="Filter by severity"),
    status: Optional[FindingStatus] = Query(None, description="Filter by status"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    List security findings for an account
    
    Returns all security findings with optional filtering by:
    - Severity (critical, high, medium, low)
    - Status (open, in_progress, resolved, ignored)
    - Resource type (ec2_instance, s3_bucket, etc.)
    """
    customer_id = current_user.get("sub")
    
    # Verify account ownership
    account = db.query(Account).filter(
        Account.id == account_id,
        Account.customer_id == customer_id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account {account_id} not found"
        )
    
    # Build query
    query = db.query(SecurityFinding).filter(
        SecurityFinding.account_id == account_id
    )
    
    if severity:
        query = query.filter(SecurityFinding.severity == severity)
    
    if status:
        query = query.filter(SecurityFinding.status == status)
    
    if resource_type:
        query = query.filter(SecurityFinding.resource_type == resource_type)
    
    # Order by severity (critical first) and date
    severity_order = {
        Severity.CRITICAL: 0,
        Severity.HIGH: 1,
        Severity.MEDIUM: 2,
        Severity.LOW: 3,
        Severity.INFO: 4
    }
    
    findings = query.order_by(
        SecurityFinding.detected_at.desc()
    ).offset(offset).limit(limit).all()
    
    # Sort by severity in Python (since SQL doesn't know our enum order)
    findings_sorted = sorted(
        findings,
        key=lambda f: (severity_order.get(f.severity, 99), f.detected_at),
        reverse=True
    )
    
    return [finding.to_dict() for finding in findings_sorted]


@router.get("/{account_id}/summary", response_model=SecuritySummaryResponse)
async def get_security_summary(
    account_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get security summary for an account
    
    Returns overview of all security findings with breakdowns
    by severity, status, and compliance scores
    """
    customer_id = current_user.get("sub")
    
    # Verify account ownership
    account = db.query(Account).filter(
        Account.id == account_id,
        Account.customer_id == customer_id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account {account_id} not found"
        )
    
    # Get all findings
    findings = db.query(SecurityFinding).filter(
        SecurityFinding.account_id == account_id
    ).all()
    
    # Calculate severity breakdown
    severity_breakdown = {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
        "info": 0
    }
    
    for finding in findings:
        severity_breakdown[finding.severity.value] += 1
    
    # Calculate status breakdown
    status_breakdown = {
        "open": 0,
        "in_progress": 0,
        "resolved": 0,
        "ignored": 0
    }
    
    for finding in findings:
        status_breakdown[finding.status.value] += 1
    
    # Calculate compliance scores
    compliance_frameworks = {}
    for finding in findings:
        if finding.compliance_frameworks:
            for framework in finding.compliance_frameworks:
                if framework not in compliance_frameworks:
                    compliance_frameworks[framework] = {"total": 0, "failing": 0}
                compliance_frameworks[framework]["total"] += 1
                if finding.status == FindingStatus.OPEN:
                    compliance_frameworks[framework]["failing"] += 1
    
    # Calculate compliance percentages
    compliance_scores = {}
    for framework, counts in compliance_frameworks.items():
        passing = counts["total"] - counts["failing"]
        percentage = (passing / counts["total"] * 100) if counts["total"] > 0 else 100
        compliance_scores[framework] = round(percentage, 1)
    
    return SecuritySummaryResponse(
        account_id=str(account_id),
        total_findings=len(findings),
        severity_breakdown=severity_breakdown,
        status_breakdown=status_breakdown,
        compliance_scores=compliance_scores,
        last_scan_at=account.last_security_scan_at.isoformat() if account.last_security_scan_at else None
    )


@router.post("/{account_id}/scan")
async def run_security_scan(
    account_id: UUID,
    full_scan: bool = Query(True, description="Run full scan or incremental"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Run security scan on the account
    
    This endpoint:
    1. Connects to the AWS account
    2. Runs 100+ security checks
    3. Stores findings in the database
    4. Returns summary of findings
    """
    customer_id = current_user.get("sub")
    
    # Verify account ownership
    account = db.query(Account).filter(
        Account.id == account_id,
        Account.customer_id == customer_id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account {account_id} not found"
        )
    
    try:
        # Initialize security scanner
        aws_client = AWSClient(account.role_arn, account.external_id)
        scanner = SecurityScanner(aws_client)
        
        # Run full scan
        findings_data = scanner.run_full_scan()
        
        # Save findings to database
        new_findings_count = 0
        for finding_data in findings_data:
            # Check if finding already exists
            existing = db.query(SecurityFinding).filter(
                SecurityFinding.account_id == account_id,
                SecurityFinding.resource_id == finding_data.get("resource_id"),
                SecurityFinding.check_id == finding_data.get("check_id"),
                SecurityFinding.status != FindingStatus.RESOLVED
            ).first()
            
            if existing:
                # Update existing finding
                existing.last_checked_at = datetime.utcnow()
                existing.evidence = finding_data.get("evidence")
            else:
                # Create new finding
                finding = SecurityFinding(
                    account_id=account_id,
                    resource_id=finding_data.get("resource_id"),
                    resource_type=finding_data.get("resource_type"),
                    region=finding_data.get("region"),
                    check_id=finding_data.get("check_id"),
                    check_name=finding_data.get("check_name"),
                    title=finding_data.get("title"),
                    description=finding_data.get("description"),
                    severity=finding_data.get("severity"),
                    remediation=finding_data.get("remediation"),
                    evidence=finding_data.get("evidence"),
                    compliance_frameworks=finding_data.get("compliance_frameworks"),
                    compliance_controls=finding_data.get("compliance_controls"),
                    status=FindingStatus.OPEN,
                    detected_at=datetime.utcnow(),
                    first_detected_at=datetime.utcnow(),
                    last_checked_at=datetime.utcnow(),
                    can_auto_remediate=finding_data.get("can_auto_remediate")
                )
                db.add(finding)
                new_findings_count += 1
        
        # Update account last scan time
        account.last_security_scan_at = datetime.utcnow()
        
        db.commit()
        
        # Calculate summary
        severity_counts = {}
        for finding in findings_data:
            sev = finding.get("severity").value if hasattr(finding.get("severity"), 'value') else finding.get("severity")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
        
        return {
            "account_id": str(account_id),
            "scan_completed_at": datetime.utcnow().isoformat(),
            "findings_count": len(findings_data),
            "new_findings": new_findings_count,
            "severity_breakdown": severity_counts,
            "message": f"Security scan completed. Found {len(findings_data)} issues ({new_findings_count} new)"
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Security scan failed: {str(e)}"
        )


@router.get("/{account_id}/finding/{finding_id}", response_model=SecurityFindingResponse)
async def get_finding_detail(
    account_id: UUID,
    finding_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get detailed information about a specific finding"""
    customer_id = current_user.get("sub")
    
    # Verify account ownership
    account = db.query(Account).filter(
        Account.id == account_id,
        Account.customer_id == customer_id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account {account_id} not found"
        )
    
    finding = db.query(SecurityFinding).filter(
        SecurityFinding.id == finding_id,
        SecurityFinding.account_id == account_id
    ).first()
    
    if not finding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Finding {finding_id} not found"
        )
    
    return finding.to_dict()


@router.patch("/{account_id}/finding/{finding_id}/status")
async def update_finding_status(
    account_id: UUID,
    finding_id: UUID,
    new_status: FindingStatus,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update the status of a security finding
    
    Statuses:
    - open: Issue is unresolved
    - in_progress: Work is underway
    - resolved: Issue has been fixed
    - ignored: Issue is accepted risk
    - false_positive: Issue is not actually a problem
    """
    customer_id = current_user.get("sub")
    
    # Verify account ownership
    account = db.query(Account).filter(
        Account.id == account_id,
        Account.customer_id == customer_id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account {account_id} not found"
        )
    
    finding = db.query(SecurityFinding).filter(
        SecurityFinding.id == finding_id,
        SecurityFinding.account_id == account_id
    ).first()
    
    if not finding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Finding {finding_id} not found"
        )
    
    # Update status
    old_status = finding.status
    finding.status = new_status
    finding.status_reason = reason
    
    if new_status == FindingStatus.RESOLVED:
        finding.resolved_at = datetime.utcnow()
    
    # TODO: Log status change for audit
    
    db.commit()
    
    return {
        "finding_id": str(finding_id),
        "old_status": old_status.value,
        "new_status": new_status.value,
        "message": f"Finding status updated from {old_status.value} to {new_status.value}"
    }


@router.get("/{account_id}/compliance/{framework}", response_model=ComplianceReportResponse)
async def get_compliance_report(
    account_id: UUID,
    framework: str = Query(..., regex="^(CIS|PCI-DSS|HIPAA|SOC2)$"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get compliance report for a specific framework
    
    Supported frameworks:
    - CIS: CIS AWS Foundations Benchmark
    - PCI-DSS: Payment Card Industry Data Security Standard
    - HIPAA: Health Insurance Portability and Accountability Act
    - SOC2: Service Organization Control 2
    """
    customer_id = current_user.get("sub")
    
    # Verify account ownership
    account = db.query(Account).filter(
        Account.id == account_id,
        Account.customer_id == customer_id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account {account_id} not found"
        )
    
    # Get findings for this framework
    findings = db.query(SecurityFinding).filter(
        SecurityFinding.account_id == account_id,
        SecurityFinding.compliance_frameworks.contains([framework])
    ).all()
    
    # Calculate compliance
    total_controls = len(findings)
    failing_controls = len([f for f in findings if f.status == FindingStatus.OPEN])
    passing_controls = total_controls - failing_controls
    
    compliance_percentage = (passing_controls / total_controls * 100) if total_controls > 0 else 100
    
    # Group findings by control
    findings_by_control = {}
    for finding in findings:
        for control in finding.compliance_controls or []:
            if control not in findings_by_control:
                findings_by_control[control] = []
            findings_by_control[control].append({
                "title": finding.title,
                "severity": finding.severity.value,
                "status": finding.status.value,
                "resource_id": finding.resource_id
            })
    
    findings_list = [
        {
            "control": control,
            "findings": findings_data
        }
        for control, findings_data in findings_by_control.items()
    ]
    
    return ComplianceReportResponse(
        framework=framework,
        total_controls=total_controls,
        passing_controls=passing_controls,
        failing_controls=failing_controls,
        compliance_percentage=round(compliance_percentage, 1),
        findings=findings_list
    )


@router.get("/{account_id}/exportreport")
async def export_security_report(
    account_id: UUID,
    format: str = Query("json", regex="^(json|csv|pdf)$"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Export security report in various formats
    
    Formats:
    - json: JSON format (ready to use)
    - csv: CSV format (for Excel)
    - pdf: PDF format (for sharing)
    """
    customer_id = current_user.get("sub")
    
    # Verify account ownership
    account = db.query(Account).filter(
        Account.id == account_id,
        Account.customer_id == customer_id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account {account_id} not found"
        )
    
    # TODO: Implement actual export functionality
    # For now, return JSON
    
    findings = db.query(SecurityFinding).filter(
        SecurityFinding.account_id == account_id
    ).all()
    
    report_data = {
        "account_id": str(account_id),
        "account_name": account.aws_account_name,
        "generated_at": datetime.utcnow().isoformat(),
        "total_findings": len(findings),
        "findings": [finding.to_dict() for finding in findings]
    }
    
    return report_data
