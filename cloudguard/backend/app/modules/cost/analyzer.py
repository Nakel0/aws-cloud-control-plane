"""
Cost Analyzer - Aggregates cost data and generates insights
"""

from datetime import datetime, timedelta
from typing import Optional
import structlog

from app.core.aws_client import AWSClientManager
from app.core.config import get_settings
from app.models.schemas import CostSummary, CostFinding

logger = structlog.get_logger()


class CostAnalyzer:
    """
    Analyzes AWS Cost Explorer data to provide:
    - Current spend breakdown
    - Spend trends
    - Cost anomaly detection
    - Budget tracking
    """
    
    def __init__(self, aws_client: AWSClientManager):
        self.aws = aws_client
        self.settings = get_settings()
    
    async def get_cost_summary(
        self, 
        findings: list[CostFinding],
        days: int = 30
    ) -> CostSummary:
        """Generate cost summary with findings"""
        
        # Get actual spend from Cost Explorer
        total_spend = await self._get_total_spend(days)
        trend_data = await self._get_daily_costs(days)
        
        # Calculate savings from findings
        potential_savings = sum(f.estimated_savings or 0 for f in findings)
        
        # Group findings by severity
        findings_by_severity = {
            "critical": len([f for f in findings if f.severity.value == "critical"]),
            "high": len([f for f in findings if f.severity.value == "high"]),
            "medium": len([f for f in findings if f.severity.value == "medium"]),
            "low": len([f for f in findings if f.severity.value == "low"]),
        }
        
        # Group by waste type
        waste_categories = {}
        for finding in findings:
            waste_type = getattr(finding, "waste_type", "other")
            if waste_type not in waste_categories:
                waste_categories[waste_type] = {"count": 0, "savings": 0}
            waste_categories[waste_type]["count"] += 1
            waste_categories[waste_type]["savings"] += finding.estimated_savings or 0
        
        top_waste = sorted(
            [{"type": k, **v} for k, v in waste_categories.items()],
            key=lambda x: x["savings"],
            reverse=True
        )[:5]
        
        return CostSummary(
            total_monthly_spend=total_spend,
            potential_monthly_savings=potential_savings,
            savings_percentage=(potential_savings / total_spend * 100) if total_spend > 0 else 0,
            findings_count=len(findings),
            findings_by_severity=findings_by_severity,
            top_waste_categories=top_waste,
            trend_30d=trend_data,
        )
    
    async def _get_total_spend(self, days: int = 30) -> float:
        """Get total spend for the period"""
        try:
            ce = self.aws.ce
            
            end_date = datetime.utcnow().strftime("%Y-%m-%d")
            start_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
            
            response = ce.get_cost_and_usage(
                TimePeriod={"Start": start_date, "End": end_date},
                Granularity="MONTHLY",
                Metrics=["UnblendedCost"],
            )
            
            total = sum(
                float(result["Total"]["UnblendedCost"]["Amount"])
                for result in response.get("ResultsByTime", [])
            )
            
            return total
            
        except Exception as e:
            logger.error("Error getting total spend", error=str(e))
            return 0.0
    
    async def _get_daily_costs(self, days: int = 30) -> list[dict]:
        """Get daily cost trend"""
        try:
            ce = self.aws.ce
            
            end_date = datetime.utcnow().strftime("%Y-%m-%d")
            start_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
            
            response = ce.get_cost_and_usage(
                TimePeriod={"Start": start_date, "End": end_date},
                Granularity="DAILY",
                Metrics=["UnblendedCost"],
            )
            
            return [
                {
                    "date": result["TimePeriod"]["Start"],
                    "cost": float(result["Total"]["UnblendedCost"]["Amount"]),
                }
                for result in response.get("ResultsByTime", [])
            ]
            
        except Exception as e:
            logger.error("Error getting daily costs", error=str(e))
            return []
    
    async def get_cost_by_service(self, days: int = 30) -> dict[str, float]:
        """Get cost breakdown by service"""
        try:
            ce = self.aws.ce
            
            end_date = datetime.utcnow().strftime("%Y-%m-%d")
            start_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
            
            response = ce.get_cost_and_usage(
                TimePeriod={"Start": start_date, "End": end_date},
                Granularity="MONTHLY",
                Metrics=["UnblendedCost"],
                GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
            )
            
            costs = {}
            for result in response.get("ResultsByTime", []):
                for group in result.get("Groups", []):
                    service = group["Keys"][0]
                    cost = float(group["Metrics"]["UnblendedCost"]["Amount"])
                    costs[service] = costs.get(service, 0) + cost
            
            return dict(sorted(costs.items(), key=lambda x: x[1], reverse=True))
            
        except Exception as e:
            logger.error("Error getting cost by service", error=str(e))
            return {}
    
    async def detect_cost_anomalies(self, threshold_percentage: float = 20.0) -> list[dict]:
        """Detect unusual cost spikes"""
        try:
            ce = self.aws.ce
            
            # Get anomalies from AWS Cost Anomaly Detection if available
            # Fallback to simple detection
            daily_costs = await self._get_daily_costs(14)
            
            if len(daily_costs) < 7:
                return []
            
            # Calculate rolling average
            anomalies = []
            for i in range(7, len(daily_costs)):
                window = daily_costs[i-7:i]
                avg = sum(d["cost"] for d in window) / 7
                current = daily_costs[i]["cost"]
                
                if avg > 0:
                    deviation = ((current - avg) / avg) * 100
                    if deviation > threshold_percentage:
                        anomalies.append({
                            "date": daily_costs[i]["date"],
                            "expected": avg,
                            "actual": current,
                            "deviation_percentage": deviation,
                        })
            
            return anomalies
            
        except Exception as e:
            logger.error("Error detecting cost anomalies", error=str(e))
            return []
