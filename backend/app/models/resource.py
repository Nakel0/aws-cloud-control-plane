"""
AWS Resource model
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class Resource(Base):
    """
    AWS Resource model
    
    Represents any AWS resource discovered by CloudGuard
    (EC2, RDS, S3, Lambda, etc.)
    """
    __tablename__ = "resources"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Resource Identification
    resource_id = Column(String(255), nullable=False, index=True)  # ARN or resource ID
    resource_type = Column(String(50), nullable=False, index=True)  # ec2_instance, rds_instance, s3_bucket, etc.
    resource_name = Column(String(255))
    
    # Location
    region = Column(String(50), nullable=False, index=True)
    availability_zone = Column(String(50))
    
    # Resource Details
    state = Column(String(50))  # running, stopped, available, etc.
    tags = Column(JSONB, default=dict)
    metadata = Column(JSONB, default=dict)  # Service-specific details
    
    # Cost Information
    monthly_cost = Column(JSONB)  # Estimated monthly cost
    
    # Discovery
    discovered_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    last_seen_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    account = relationship("Account", back_populates="resources")
    
    # Composite indexes for common queries
    __table_args__ = (
        Index("idx_account_resource_type", "account_id", "resource_type"),
        Index("idx_account_region", "account_id", "region"),
    )
    
    def __repr__(self):
        return f"<Resource {self.resource_type}:{self.resource_id}>"
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "account_id": str(self.account_id),
            "resource_id": self.resource_id,
            "resource_type": self.resource_type,
            "resource_name": self.resource_name,
            "region": self.region,
            "state": self.state,
            "tags": self.tags,
            "monthly_cost": self.monthly_cost,
            "discovered_at": self.discovered_at.isoformat(),
            "last_seen_at": self.last_seen_at.isoformat()
        }
