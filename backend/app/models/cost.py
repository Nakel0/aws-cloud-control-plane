"""
Cost data model (TimescaleDB hypertable)
"""
from sqlalchemy import Column, String, DateTime, Numeric, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class CostData(Base):
    """
    Cost data model for time-series storage
    
    This table will be converted to a TimescaleDB hypertable
    for efficient time-series queries
    """
    __tablename__ = "cost_data"
    
    # TimescaleDB requires time column for partitioning
    time = Column(DateTime(timezone=True), nullable=False, primary_key=True)
    
    # Dimensions
    account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
        index=True
    )
    service = Column(String(100), nullable=False, primary_key=True, index=True)
    resource_id = Column(String(255), primary_key=True)
    region = Column(String(50))
    
    # Metrics
    cost = Column(Numeric(10, 2), nullable=False)  # Cost in USD
    usage_amount = Column(Numeric(15, 4))
    usage_unit = Column(String(50))
    
    # Additional dimensions
    tags = Column(String(1000))  # JSON string of resource tags
    charge_type = Column(String(50))  # Usage, Tax, Refund, etc.
    
    # Relationships
    account = relationship("Account", back_populates="cost_data")
    
    # Indexes for common queries
    __table_args__ = (
        Index("idx_cost_time_account", "time", "account_id"),
        Index("idx_cost_time_service", "time", "service"),
    )
    
    def __repr__(self):
        return f"<CostData {self.time} {self.service} ${self.cost}>"
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "time": self.time.isoformat(),
            "account_id": str(self.account_id),
            "service": self.service,
            "resource_id": self.resource_id,
            "region": self.region,
            "cost": float(self.cost),
            "usage_amount": float(self.usage_amount) if self.usage_amount else None,
            "usage_unit": self.usage_unit
        }


# SQL to convert to hypertable (run after table creation):
# SELECT create_hypertable('cost_data', 'time', chunk_time_interval => INTERVAL '1 day');
