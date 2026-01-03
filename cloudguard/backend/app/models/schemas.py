"""
Pydantic schemas for API requests and responses
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field


# ============ Enums ============

class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingCategory(str, Enum):
    COST = "cost"
    SECURITY = "security"
    RELIABILITY = "reliability"


class ResourceType(str, Enum):
    EC2_INSTANCE = "ec2:instance"
    EC2_VOLUME = "ec2:volume"
    EC2_SNAPSHOT = "ec2:snapshot"
    EC2_EIP = "ec2:eip"
    EC2_AMI = "ec2:ami"
    RDS_INSTANCE = "rds:instance"
    RDS_SNAPSHOT = "rds:snapshot"
    S3_BUCKET = "s3:bucket"
    LAMBDA_FUNCTION = "lambda:function"
    ELB = "elb:loadbalancer"
    EBS_VOLUME = "ebs:volume"
    IAM_USER = "iam:user"
    IAM_ROLE = "iam:role"
    SECURITY_GROUP = "ec2:security-group"


class RemediationStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


# ============ Base Schemas ============

class ResourceBase(BaseModel):
    """Base resource information"""
    resource_id: str
    resource_type: ResourceType
    resource_name: Optional[str] = None
    region: str
    account_id: str
    tags: dict[str, str] = Field(default_factory=dict)
    created_at: Optional[datetime] = None


class FindingBase(BaseModel):
    """Base finding/recommendation"""
    finding_id: str
    category: FindingCategory
    severity: Severity
    title: str
    description: str
    resource: ResourceBase
    recommendation: str
    estimated_savings: Optional[float] = None  # Monthly USD
    remediation_available: bool = False
    detected_at: datetime = Field(default_factory=datetime.utcnow)


# ============ Cost Schemas ============

class CostFinding(FindingBase):
    """Cost optimization finding"""
    category: FindingCategory = FindingCategory.COST
    current_monthly_cost: float
    optimized_monthly_cost: Optional[float] = None
    savings_percentage: Optional[float] = None
    waste_type: str  # idle, oversized, unattached, etc.


class IdleResourceFinding(CostFinding):
    """Idle resource detection"""
    waste_type: str = "idle"
    idle_days: int
    last_activity: Optional[datetime] = None
    utilization_metrics: dict[str, float] = Field(default_factory=dict)


class OversizedResourceFinding(CostFinding):
    """Oversized resource (rightsizing opportunity)"""
    waste_type: str = "oversized"
    current_size: str
    recommended_size: str
    avg_cpu_utilization: float
    avg_memory_utilization: Optional[float] = None
    peak_cpu_utilization: float


class UnattachedResourceFinding(CostFinding):
    """Unattached resources (EBS volumes, EIPs, etc.)"""
    waste_type: str = "unattached"
    unattached_days: int


class ReservedInstanceOpportunity(CostFinding):
    """Reserved Instance or Savings Plan recommendation"""
    waste_type: str = "on_demand_usage"
    on_demand_hours: float
    recommended_commitment: str  # 1yr-no-upfront, 1yr-partial, 3yr-all-upfront
    break_even_months: int


# ============ Security Schemas ============

class SecurityFinding(FindingBase):
    """Security misconfiguration finding"""
    category: FindingCategory = FindingCategory.SECURITY
    compliance_frameworks: list[str] = Field(default_factory=list)  # CIS, SOC2, etc.
    cwe_id: Optional[str] = None
    attack_vector: Optional[str] = None


class PublicAccessFinding(SecurityFinding):
    """Public access misconfiguration"""
    public_access_type: str  # s3_bucket, security_group, rds, etc.
    exposed_ports: list[int] = Field(default_factory=list)
    exposed_to: str = "0.0.0.0/0"


class EncryptionFinding(SecurityFinding):
    """Missing encryption finding"""
    encryption_type: str  # at_rest, in_transit
    data_classification: Optional[str] = None


class IAMFinding(SecurityFinding):
    """IAM misconfiguration"""
    iam_issue_type: str  # overly_permissive, unused_credentials, no_mfa, etc.
    affected_permissions: list[str] = Field(default_factory=list)
    last_used: Optional[datetime] = None


# ============ Reliability Schemas ============

class ReliabilityFinding(FindingBase):
    """Reliability/resilience finding"""
    category: FindingCategory = FindingCategory.RELIABILITY
    availability_impact: str  # high, medium, low
    mttr_impact: Optional[str] = None  # Mean Time To Recovery


class SingleAZFinding(ReliabilityFinding):
    """Single availability zone risk"""
    current_az: str
    recommended_azs: list[str]


class NoBackupFinding(ReliabilityFinding):
    """Missing backup configuration"""
    resource_age_days: int
    data_size_gb: Optional[float] = None
    recommended_backup_frequency: str


class NoAutoScalingFinding(ReliabilityFinding):
    """Missing auto-scaling configuration"""
    current_instance_count: int
    peak_load_period: Optional[str] = None
    recommended_min: int
    recommended_max: int


class HealthCheckFinding(ReliabilityFinding):
    """Missing or misconfigured health checks"""
    health_check_type: str
    current_config: Optional[dict] = None
    recommended_config: dict


# ============ Dashboard Schemas ============

class CostSummary(BaseModel):
    """Cost optimization summary"""
    total_monthly_spend: float
    potential_monthly_savings: float
    savings_percentage: float
    findings_count: int
    findings_by_severity: dict[str, int]
    top_waste_categories: list[dict[str, Any]]
    trend_30d: list[dict[str, float]]  # Daily cost trend


class SecuritySummary(BaseModel):
    """Security posture summary"""
    security_score: int  # 0-100
    critical_findings: int
    high_findings: int
    medium_findings: int
    low_findings: int
    compliance_status: dict[str, float]  # Framework -> compliance %
    public_resources: int
    unencrypted_resources: int


class ReliabilitySummary(BaseModel):
    """Reliability posture summary"""
    reliability_score: int  # 0-100
    single_az_resources: int
    resources_without_backup: int
    resources_without_monitoring: int
    estimated_availability: float  # Percentage


class DashboardSummary(BaseModel):
    """Complete dashboard summary"""
    account_id: str
    last_scan: datetime
    cost: CostSummary
    security: SecuritySummary
    reliability: ReliabilitySummary
    total_resources_scanned: int
    total_findings: int


# ============ Remediation Schemas ============

class RemediationAction(BaseModel):
    """Remediation action details"""
    action_id: str
    finding_id: str
    action_type: str
    description: str
    is_reversible: bool
    requires_approval: bool
    estimated_impact: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class RemediationResult(BaseModel):
    """Result of remediation action"""
    action_id: str
    status: RemediationStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    result_message: str
    rollback_available: bool = False


# ============ Scan Schemas ============

class ScanRequest(BaseModel):
    """Request to initiate a scan"""
    regions: list[str] = Field(default=["us-east-1"])
    categories: list[FindingCategory] = Field(
        default=[FindingCategory.COST, FindingCategory.SECURITY, FindingCategory.RELIABILITY]
    )
    resource_types: Optional[list[ResourceType]] = None


class ScanStatus(BaseModel):
    """Scan progress status"""
    scan_id: str
    status: str  # pending, running, completed, failed
    started_at: datetime
    completed_at: Optional[datetime] = None
    progress_percentage: int
    resources_scanned: int
    findings_count: int
    errors: list[str] = Field(default_factory=list)
