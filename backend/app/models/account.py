"""
AWS Account model
"""
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class AccountStatus(str, enum.Enum):
    """Account connection status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    PENDING = "pending"


class Account(Base):
    """
    AWS Account model
    
    Represents a connected AWS account that CloudGuard monitors
    """
    __tablename__ = "accounts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # AWS Details
    aws_account_id = Column(String(12), nullable=False, unique=True, index=True)
    aws_account_name = Column(String(255))
    role_arn = Column(String(512), nullable=False)  # For cross-account access
    external_id = Column(String(255))  # For additional security
    
    # Status
    status = Column(SQLEnum(AccountStatus), default=AccountStatus.PENDING, nullable=False)
    status_message = Column(String(1000))
    
    # Metadata
    tags = Column(JSONB, default=dict)  # Custom tags
    metadata = Column(JSONB, default=dict)  # Additional metadata
    
    # Scanning
    last_scan_at = Column(DateTime(timezone=True))
    last_cost_sync_at = Column(DateTime(timezone=True))
    last_security_scan_at = Column(DateTime(timezone=True))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    resources = relationship("Resource", back_populates="account", cascade="all, delete-orphan")
    cost_data = relationship("CostData", back_populates="account", cascade="all, delete-orphan")
    security_findings = relationship("SecurityFinding", back_populates="account", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="account", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Account {self.aws_account_id} ({self.status})>"
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "customer_id": str(self.customer_id),
            "aws_account_id": self.aws_account_id,
            "aws_account_name": self.aws_account_name,
            "status": self.status.value,
            "status_message": self.status_message,
            "last_scan_at": self.last_scan_at.isoformat() if self.last_scan_at else None,
            "created_at": self.created_at.isoformat(),
            "tags": self.tags
        }
