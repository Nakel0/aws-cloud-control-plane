"""
API Routes for CloudGuard
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel
import structlog

from app.core.aws_client import get_aws_client, AWSClientManager
from app.core.config import get_settings
from app.models.schemas import (
    DashboardSummary,
    CostSummary,
    SecuritySummary,
    ReliabilitySummary,
    ScanRequest,
    ScanStatus,
    FindingCategory,
    RemediationAction,
    RemediationResult,
    RemediationStatus,
)
from app.modules.cost import CostScanner, CostAnalyzer
from app.modules.security import SecurityScanner
from app.modules.reliability import ReliabilityScanner
from app.services.remediation import RemediationEngine

logger = structlog.get_logger()
router = APIRouter()

# In-memory storage for demo (use Redis/DB in production)
_scan_results = {}
_scan_status = {}


# ============ Health & Info ============

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@router.get("/info")
async def get_info():
    """Get application info"""
    settings = get_settings()
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


# ============ Dashboard ============

@router.get("/dashboard", response_model=DashboardSummary)
async def get_dashboard(region: Optional[str] = None):
    """Get complete dashboard summary"""
    try:
        aws = get_aws_client(region)
        settings = get_settings()
        
        # Run all scanners
        cost_scanner = CostScanner(aws)
        security_scanner = SecurityScanner(aws)
        reliability_scanner = ReliabilityScanner(aws)
        
        regions = [region] if region else [settings.aws_region]
        
        cost_findings = await cost_scanner.scan_all(regions)
        security_findings = await security_scanner.scan_all(regions)
        reliability_findings = await reliability_scanner.scan_all(regions)
        
        # Generate summaries
        cost_analyzer = CostAnalyzer(aws)
        cost_summary = await cost_analyzer.get_cost_summary(cost_findings)
        
        # Security summary
        security_summary = SecuritySummary(
            security_score=_calculate_security_score(security_findings),
            critical_findings=len([f for f in security_findings if f.severity.value == "critical"]),
            high_findings=len([f for f in security_findings if f.severity.value == "high"]),
            medium_findings=len([f for f in security_findings if f.severity.value == "medium"]),
            low_findings=len([f for f in security_findings if f.severity.value == "low"]),
            compliance_status={
                "CIS AWS": 75.0,  # Would calculate from findings
                "SOC2": 80.0,
                "PCI-DSS": 70.0,
            },
            public_resources=len([f for f in security_findings if hasattr(f, "public_access_type")]),
            unencrypted_resources=len([f for f in security_findings if hasattr(f, "encryption_type")]),
        )
        
        # Reliability summary
        reliability_summary = ReliabilitySummary(
            reliability_score=_calculate_reliability_score(reliability_findings),
            single_az_resources=len([f for f in reliability_findings if hasattr(f, "current_az")]),
            resources_without_backup=len([f for f in reliability_findings if hasattr(f, "recommended_backup_frequency")]),
            resources_without_monitoring=len([f for f in reliability_findings if hasattr(f, "health_check_type")]),
            estimated_availability=99.5,  # Would calculate from findings
        )
        
        return DashboardSummary(
            account_id=_get_account_id(aws),
            last_scan=datetime.utcnow(),
            cost=cost_summary,
            security=security_summary,
            reliability=reliability_summary,
            total_resources_scanned=len(cost_findings) + len(security_findings) + len(reliability_findings),
            total_findings=len(cost_findings) + len(security_findings) + len(reliability_findings),
        )
        
    except Exception as e:
        logger.error("Error generating dashboard", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ============ Scans ============

@router.post("/scans", response_model=ScanStatus)
async def start_scan(
    request: ScanRequest,
    background_tasks: BackgroundTasks,
):
    """Start a new scan"""
    import uuid
    
    scan_id = str(uuid.uuid4())
    
    _scan_status[scan_id] = ScanStatus(
        scan_id=scan_id,
        status="pending",
        started_at=datetime.utcnow(),
        progress_percentage=0,
        resources_scanned=0,
        findings_count=0,
    )
    
    # Run scan in background
    background_tasks.add_task(_run_scan, scan_id, request)
    
    return _scan_status[scan_id]


@router.get("/scans/{scan_id}", response_model=ScanStatus)
async def get_scan_status(scan_id: str):
    """Get scan status"""
    if scan_id not in _scan_status:
        raise HTTPException(status_code=404, detail="Scan not found")
    return _scan_status[scan_id]


# ============ Findings ============

@router.get("/findings")
async def list_findings(
    category: Optional[FindingCategory] = None,
    severity: Optional[str] = None,
    region: Optional[str] = None,
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0, ge=0),
):
    """List all findings with optional filters"""
    try:
        aws = get_aws_client(region)
        settings = get_settings()
        regions = [region] if region else [settings.aws_region]
        
        all_findings = []
        
        if category is None or category == FindingCategory.COST:
            scanner = CostScanner(aws)
            all_findings.extend(await scanner.scan_all(regions))
        
        if category is None or category == FindingCategory.SECURITY:
            scanner = SecurityScanner(aws)
            all_findings.extend(await scanner.scan_all(regions))
        
        if category is None or category == FindingCategory.RELIABILITY:
            scanner = ReliabilityScanner(aws)
            all_findings.extend(await scanner.scan_all(regions))
        
        # Filter by severity
        if severity:
            all_findings = [f for f in all_findings if f.severity.value == severity]
        
        # Paginate
        total = len(all_findings)
        findings = all_findings[offset:offset + limit]
        
        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "findings": [f.model_dump() for f in findings],
        }
        
    except Exception as e:
        logger.error("Error listing findings", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/findings/{finding_id}")
async def get_finding(finding_id: str):
    """Get specific finding details"""
    # Would look up from database in production
    raise HTTPException(status_code=404, detail="Finding not found")


# ============ Cost ============

@router.get("/cost/summary", response_model=CostSummary)
async def get_cost_summary(region: Optional[str] = None):
    """Get cost optimization summary"""
    try:
        aws = get_aws_client(region)
        settings = get_settings()
        
        scanner = CostScanner(aws)
        analyzer = CostAnalyzer(aws)
        
        regions = [region] if region else [settings.aws_region]
        findings = await scanner.scan_all(regions)
        
        return await analyzer.get_cost_summary(findings)
        
    except Exception as e:
        logger.error("Error getting cost summary", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cost/by-service")
async def get_cost_by_service(days: int = Query(default=30, le=90)):
    """Get cost breakdown by AWS service"""
    try:
        aws = get_aws_client()
        analyzer = CostAnalyzer(aws)
        
        return await analyzer.get_cost_by_service(days)
        
    except Exception as e:
        logger.error("Error getting cost by service", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cost/anomalies")
async def get_cost_anomalies(threshold: float = Query(default=20.0)):
    """Detect cost anomalies"""
    try:
        aws = get_aws_client()
        analyzer = CostAnalyzer(aws)
        
        return await analyzer.detect_cost_anomalies(threshold)
        
    except Exception as e:
        logger.error("Error detecting cost anomalies", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ============ Security ============

@router.get("/security/summary", response_model=SecuritySummary)
async def get_security_summary(region: Optional[str] = None):
    """Get security posture summary"""
    try:
        aws = get_aws_client(region)
        settings = get_settings()
        
        scanner = SecurityScanner(aws)
        regions = [region] if region else [settings.aws_region]
        findings = await scanner.scan_all(regions)
        
        return SecuritySummary(
            security_score=_calculate_security_score(findings),
            critical_findings=len([f for f in findings if f.severity.value == "critical"]),
            high_findings=len([f for f in findings if f.severity.value == "high"]),
            medium_findings=len([f for f in findings if f.severity.value == "medium"]),
            low_findings=len([f for f in findings if f.severity.value == "low"]),
            compliance_status={"CIS AWS": 75.0, "SOC2": 80.0},
            public_resources=len([f for f in findings if hasattr(f, "public_access_type")]),
            unencrypted_resources=len([f for f in findings if hasattr(f, "encryption_type")]),
        )
        
    except Exception as e:
        logger.error("Error getting security summary", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ============ Reliability ============

@router.get("/reliability/summary", response_model=ReliabilitySummary)
async def get_reliability_summary(region: Optional[str] = None):
    """Get reliability posture summary"""
    try:
        aws = get_aws_client(region)
        settings = get_settings()
        
        scanner = ReliabilityScanner(aws)
        regions = [region] if region else [settings.aws_region]
        findings = await scanner.scan_all(regions)
        
        return ReliabilitySummary(
            reliability_score=_calculate_reliability_score(findings),
            single_az_resources=len([f for f in findings if hasattr(f, "current_az")]),
            resources_without_backup=len([f for f in findings if hasattr(f, "recommended_backup_frequency")]),
            resources_without_monitoring=len([f for f in findings if hasattr(f, "health_check_type")]),
            estimated_availability=99.5,
        )
        
    except Exception as e:
        logger.error("Error getting reliability summary", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ============ Remediation ============

@router.post("/remediate/{finding_id}", response_model=RemediationResult)
async def remediate_finding(
    finding_id: str,
    dry_run: bool = Query(default=True),
):
    """Execute remediation for a finding"""
    try:
        aws = get_aws_client()
        engine = RemediationEngine(aws)
        
        result = await engine.remediate(finding_id, dry_run=dry_run)
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error executing remediation", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/remediation-actions/{finding_id}")
async def get_remediation_actions(finding_id: str):
    """Get available remediation actions for a finding"""
    try:
        aws = get_aws_client()
        engine = RemediationEngine(aws)
        
        actions = await engine.get_available_actions(finding_id)
        
        return {"finding_id": finding_id, "actions": [a.model_dump() for a in actions]}
        
    except Exception as e:
        logger.error("Error getting remediation actions", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ============ Regions ============

@router.get("/regions")
async def list_regions():
    """List available AWS regions"""
    try:
        regions = AWSClientManager.get_all_regions()
        return {"regions": regions}
    except Exception as e:
        logger.error("Error listing regions", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ============ Helper Functions ============

def _calculate_security_score(findings) -> int:
    """Calculate security score from findings"""
    if not findings:
        return 100
    
    deductions = {
        "critical": 20,
        "high": 10,
        "medium": 5,
        "low": 2,
    }
    
    total_deduction = sum(
        deductions.get(f.severity.value, 0) for f in findings
    )
    
    return max(0, 100 - total_deduction)


def _calculate_reliability_score(findings) -> int:
    """Calculate reliability score from findings"""
    if not findings:
        return 100
    
    deductions = {
        "critical": 15,
        "high": 8,
        "medium": 4,
        "low": 1,
    }
    
    total_deduction = sum(
        deductions.get(f.severity.value, 0) for f in findings
    )
    
    return max(0, 100 - total_deduction)


def _get_account_id(aws: AWSClientManager) -> str:
    """Get AWS account ID"""
    try:
        sts = aws.get_client("sts")
        return sts.get_caller_identity()["Account"]
    except Exception:
        return "unknown"


async def _run_scan(scan_id: str, request: ScanRequest):
    """Run scan in background"""
    try:
        _scan_status[scan_id].status = "running"
        
        aws = get_aws_client()
        all_findings = []
        
        total_steps = len(request.categories)
        completed = 0
        
        for category in request.categories:
            if category == FindingCategory.COST:
                scanner = CostScanner(aws)
                findings = await scanner.scan_all(request.regions)
                all_findings.extend(findings)
            elif category == FindingCategory.SECURITY:
                scanner = SecurityScanner(aws)
                findings = await scanner.scan_all(request.regions)
                all_findings.extend(findings)
            elif category == FindingCategory.RELIABILITY:
                scanner = ReliabilityScanner(aws)
                findings = await scanner.scan_all(request.regions)
                all_findings.extend(findings)
            
            completed += 1
            _scan_status[scan_id].progress_percentage = int((completed / total_steps) * 100)
            _scan_status[scan_id].findings_count = len(all_findings)
        
        _scan_status[scan_id].status = "completed"
        _scan_status[scan_id].completed_at = datetime.utcnow()
        _scan_results[scan_id] = all_findings
        
    except Exception as e:
        logger.error("Scan failed", scan_id=scan_id, error=str(e))
        _scan_status[scan_id].status = "failed"
        _scan_status[scan_id].errors.append(str(e))
