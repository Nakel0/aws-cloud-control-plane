"""
Security finding models
"""
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, ForeignKey, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class Severity(str, enum.Enum):
    """Security finding severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingStatus(str, enum.Enum):
    """Security finding status"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    IGNORED = "ignored"
    FALSE_POSITIVE = "false_positive"


class SecurityFinding(Base):
    """
    Security misconfiguration finding
    
    Represents a detected security issue or compliance violation
    """
    __tablename__ = "security_findings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Resource Information
    resource_id = Column(String(255), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False)
    region = Column(String(50))
    
    # Finding Details
    check_id = Column(String(100), nullable=False, index=True)  # e.g., "CIS-1.1", "S3-PUBLIC-ACCESS"
    check_name = Column(String(255), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    
    # Severity & Priority
    severity = Column(SQLEnum(Severity), nullable=False, index=True)
    cvss_score = Column(JSONB)  # CVSS scoring details
    risk_score = Column(JSONB)  # Custom risk scoring
    
    # Remediation
    remediation = Column(Text)  # How to fix
    remediation_url = Column(String(500))  # Link to docs
    can_auto_remediate = Column(JSONB)  # Auto-remediation options
    
    # Evidence
    evidence = Column(JSONB)  # Supporting data (config snapshots, etc.)
    
    # Compliance
    compliance_frameworks = Column(JSONB)  # ["CIS", "PCI-DSS", "HIPAA"]
    compliance_controls = Column(JSONB)  # Specific control IDs
    
    # Status
    status = Column(SQLEnum(FindingStatus), default=FindingStatus.OPEN, nullable=False, index=True)
    status_reason = Column(Text)  # Why was it resolved/ignored
    
    # Timestamps
    detected_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    first_detected_at = Column(DateTime(timezone=True))  # First time we saw this issue
    resolved_at = Column(DateTime(timezone=True))
    last_checked_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Assignment
    assigned_to = Column(UUID(as_uuid=True))  # User ID
    
    # Relationships
    account = relationship("Account", back_populates="security_findings")
    
    # Indexes
    __table_args__ = (
        Index("idx_security_account_status", "account_id", "status"),
        Index("idx_security_severity", "severity", "status"),
        Index("idx_security_detected_at", "detected_at"),
    )
    
    def __repr__(self):
        return f"<SecurityFinding {self.check_id} {self.severity} {self.resource_id}>"
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "account_id": str(self.account_id),
            "resource_id": self.resource_id,
            "resource_type": self.resource_type,
            "check_id": self.check_id,
            "check_name": self.check_name,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "remediation": self.remediation,
            "evidence": self.evidence,
            "compliance_frameworks": self.compliance_frameworks,
            "status": self.status.value,
            "detected_at": self.detected_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None
        }
