"""
Optimization recommendation models
"""
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, ForeignKey, Text, Numeric, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class RecommendationType(str, enum.Enum):
    """Type of recommendation"""
    COST_OPTIMIZATION = "cost_optimization"
    SECURITY = "security"
    RELIABILITY = "reliability"
    PERFORMANCE = "performance"


class Priority(str, enum.Enum):
    """Recommendation priority"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RecommendationStatus(str, enum.Enum):
    """Recommendation lifecycle status"""
    PENDING = "pending"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"
    EXPIRED = "expired"


class Recommendation(Base):
    """
    Optimization recommendation
    
    Actionable suggestions for cost, security, or reliability improvements
    """
    __tablename__ = "recommendations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Resource
    resource_id = Column(String(255), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False)
    region = Column(String(50))
    
    # Recommendation Details
    type = Column(SQLEnum(RecommendationType), nullable=False, index=True)
    priority = Column(SQLEnum(Priority), nullable=False, index=True)
    
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    rationale = Column(Text)  # Why we recommend this
    
    # Impact
    potential_savings = Column(Numeric(10, 2))  # Monthly savings in USD
    effort_level = Column(String(20))  # low, medium, high
    risk_level = Column(String(20))  # low, medium, high
    confidence = Column(Numeric(3, 2))  # 0.00 to 1.00
    
    # Actions
    actions = Column(JSONB, nullable=False)  # List of executable actions
    prerequisites = Column(JSONB)  # What needs to be done first
    
    # Evidence & Context
    evidence = Column(JSONB)  # Supporting data
    current_config = Column(JSONB)  # Current resource configuration
    recommended_config = Column(JSONB)  # Recommended configuration
    
    # Status
    status = Column(SQLEnum(RecommendationStatus), default=RecommendationStatus.PENDING, nullable=False, index=True)
    status_reason = Column(Text)
    
    # Automation
    can_auto_execute = Column(JSONB)  # Auto-execution capability
    requires_approval = Column(JSONB, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime(timezone=True))  # Some recommendations have expiry
    executed_at = Column(DateTime(timezone=True))
    
    # Assignment
    assigned_to = Column(UUID(as_uuid=True))
    approved_by = Column(UUID(as_uuid=True))
    
    # Relationships
    account = relationship("Account", back_populates="recommendations")
    automation_logs = relationship("AutomationLog", back_populates="recommendation", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_rec_account_status", "account_id", "status"),
        Index("idx_rec_type_priority", "type", "priority"),
        Index("idx_rec_created_at", "created_at"),
    )
    
    def __repr__(self):
        return f"<Recommendation {self.type} {self.priority} {self.resource_id}>"
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "account_id": str(self.account_id),
            "resource_id": self.resource_id,
            "resource_type": self.resource_type,
            "type": self.type.value,
            "priority": self.priority.value,
            "title": self.title,
            "description": self.description,
            "potential_savings": float(self.potential_savings) if self.potential_savings else None,
            "effort_level": self.effort_level,
            "risk_level": self.risk_level,
            "confidence": float(self.confidence) if self.confidence else None,
            "actions": self.actions,
            "evidence": self.evidence,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None
        }


class AutomationLog(Base):
    """
    Automation execution audit log
    
    Records every automated action taken by the platform
    """
    __tablename__ = "automation_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recommendation_id = Column(UUID(as_uuid=True), ForeignKey("recommendations.id", ondelete="CASCADE"), index=True)
    
    # Action Details
    action_type = Column(String(100), nullable=False)
    action_description = Column(Text)
    
    # Execution
    status = Column(String(20), nullable=False)  # success, failed, rolled_back
    error_message = Column(Text)
    
    # Actor
    executed_by = Column(UUID(as_uuid=True))  # User ID (or "system" for automated)
    execution_method = Column(String(50))  # manual, automatic, scheduled
    
    # AWS Details
    aws_request_id = Column(String(255))  # AWS API request ID
    aws_changes = Column(JSONB)  # What changed in AWS
    
    # Rollback
    rollback_data = Column(JSONB)  # State before change (for rollback)
    rolled_back_at = Column(DateTime(timezone=True))
    
    # Timestamps
    executed_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime(timezone=True))
    
    # Relationships
    recommendation = relationship("Recommendation", back_populates="automation_logs")
    
    def __repr__(self):
        return f"<AutomationLog {self.action_type} {self.status}>"
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "recommendation_id": str(self.recommendation_id),
            "action_type": self.action_type,
            "status": self.status,
            "error_message": self.error_message,
            "executed_by": str(self.executed_by) if self.executed_by else None,
            "execution_method": self.execution_method,
            "executed_at": self.executed_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }
