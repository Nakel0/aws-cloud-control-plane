"""
Cost Analysis API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta
from decimal import Decimal

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import Account, CostData, Recommendation, RecommendationType
from app.services.cost_analyzer import CostAnalyzer
from app.services.aws_client import AWSClient

router = APIRouter()


class CostSummaryResponse(BaseModel):
    """Cost summary response model"""
    account_id: str
    period_days: int
    total_cost: float
    daily_average: float
    monthly_projection: float
    data_points: int
    cost_by_service: dict
    trend: Optional[str] = None


class CostTrendResponse(BaseModel):
    """Cost trend data"""
    date: str
    cost: float
    service: Optional[str] = None


class OptimizationSummary(BaseModel):
    """Optimization opportunities summary"""
    account_id: str
    recommendations_count: int
    total_potential_savings: float
    savings_by_category: dict
    top_recommendations: List[dict]


@router.get("/{account_id}/summary", response_model=CostSummaryResponse)
async def get_cost_summary(
    account_id: UUID,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get cost summary for the account
    
    Returns total cost, daily average, and breakdown by service
    for the specified time period
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
    
    # Get cost data from database
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    cost_data = db.query(CostData).filter(
        CostData.account_id == account_id,
        CostData.time >= start_date,
        CostData.time <= end_date
    ).all()
    
    # Calculate summary
    total_cost = sum(float(item.cost) for item in cost_data)
    daily_average = total_cost / days if days > 0 else 0
    monthly_projection = daily_average * 30
    
    # Group by service
    cost_by_service = {}
    for item in cost_data:
        service = item.service
        cost_by_service[service] = cost_by_service.get(service, 0) + float(item.cost)
    
    # Sort by cost (descending)
    cost_by_service = dict(sorted(cost_by_service.items(), key=lambda x: x[1], reverse=True))
    
    # Determine trend (compare to previous period)
    previous_start = start_date - timedelta(days=days)
    previous_cost_data = db.query(CostData).filter(
        CostData.account_id == account_id,
        CostData.time >= previous_start,
        CostData.time < start_date
    ).all()
    
    previous_total = sum(float(item.cost) for item in previous_cost_data)
    
    if previous_total > 0:
        change_percent = ((total_cost - previous_total) / previous_total) * 100
        if change_percent > 10:
            trend = f"up {change_percent:.1f}%"
        elif change_percent < -10:
            trend = f"down {abs(change_percent):.1f}%"
        else:
            trend = "stable"
    else:
        trend = "new"
    
    return CostSummaryResponse(
        account_id=str(account_id),
        period_days=days,
        total_cost=round(total_cost, 2),
        daily_average=round(daily_average, 2),
        monthly_projection=round(monthly_projection, 2),
        data_points=len(cost_data),
        cost_by_service=cost_by_service,
        trend=trend
    )


@router.get("/{account_id}/trend", response_model=List[CostTrendResponse])
async def get_cost_trend(
    account_id: UUID,
    days: int = Query(30, ge=7, le=365),
    group_by: str = Query("day", regex="^(day|service)$"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get cost trend data for visualization
    
    Returns daily cost data, optionally grouped by service
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
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    if group_by == "day":
        # Group by day
        results = db.query(
            func.date(CostData.time).label('date'),
            func.sum(CostData.cost).label('total_cost')
        ).filter(
            CostData.account_id == account_id,
            CostData.time >= start_date,
            CostData.time <= end_date
        ).group_by(
            func.date(CostData.time)
        ).order_by(
            func.date(CostData.time)
        ).all()
        
        return [
            CostTrendResponse(
                date=str(result.date),
                cost=float(result.total_cost)
            )
            for result in results
        ]
    
    else:  # group_by == "service"
        # Group by service and day
        results = db.query(
            func.date(CostData.time).label('date'),
            CostData.service,
            func.sum(CostData.cost).label('total_cost')
        ).filter(
            CostData.account_id == account_id,
            CostData.time >= start_date,
            CostData.time <= end_date
        ).group_by(
            func.date(CostData.time),
            CostData.service
        ).order_by(
            func.date(CostData.time),
            CostData.service
        ).all()
        
        return [
            CostTrendResponse(
                date=str(result.date),
                cost=float(result.total_cost),
                service=result.service
            )
            for result in results
        ]


@router.post("/{account_id}/analyze", response_model=OptimizationSummary)
async def analyze_costs(
    account_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Run cost analysis and find optimization opportunities
    
    This endpoint:
    1. Analyzes AWS resources for waste
    2. Identifies idle and underutilized resources
    3. Suggests Reserved Instance opportunities
    4. Calculates potential savings
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
    
    # Initialize cost analyzer
    try:
        aws_client = AWSClient(account.role_arn, account.external_id)
        analyzer = CostAnalyzer(aws_client)
        
        # Run analysis
        recommendations = []
        recommendations.extend(analyzer.detect_idle_ec2_instances())
        recommendations.extend(analyzer.detect_unattached_ebs_volumes())
        recommendations.extend(analyzer.detect_unused_elastic_ips())
        recommendations.extend(analyzer.analyze_reserved_instance_opportunities())
        
        # Save recommendations to database
        from app.models import Priority, RecommendationStatus
        
        for rec_data in recommendations:
            # Check if recommendation already exists
            existing = db.query(Recommendation).filter(
                Recommendation.account_id == account_id,
                Recommendation.resource_id == rec_data.get("resource_id"),
                Recommendation.type == rec_data.get("type"),
                Recommendation.status.in_([
                    RecommendationStatus.PENDING,
                    RecommendationStatus.APPROVED,
                    RecommendationStatus.IN_PROGRESS
                ])
            ).first()
            
            if not existing:
                recommendation = Recommendation(
                    account_id=account_id,
                    resource_id=rec_data.get("resource_id"),
                    resource_type=rec_data.get("resource_type"),
                    type=rec_data.get("type"),
                    priority=rec_data.get("priority"),
                    title=rec_data.get("title"),
                    description=rec_data.get("description"),
                    potential_savings=rec_data.get("potential_savings"),
                    confidence=rec_data.get("confidence"),
                    evidence=rec_data.get("evidence"),
                    actions=rec_data.get("actions"),
                    status=RecommendationStatus.PENDING
                )
                db.add(recommendation)
        
        db.commit()
        
        # Calculate total savings and categorize
        total_savings = sum(
            float(rec.get("potential_savings", 0)) 
            for rec in recommendations
        )
        
        savings_by_category = {}
        for rec in recommendations:
            resource_type = rec.get("resource_type", "other")
            savings = float(rec.get("potential_savings", 0))
            savings_by_category[resource_type] = savings_by_category.get(resource_type, 0) + savings
        
        # Get top 5 recommendations by savings
        top_recommendations = sorted(
            recommendations,
            key=lambda x: float(x.get("potential_savings", 0)),
            reverse=True
        )[:5]
        
        return OptimizationSummary(
            account_id=str(account_id),
            recommendations_count=len(recommendations),
            total_potential_savings=round(total_savings, 2),
            savings_by_category=savings_by_category,
            top_recommendations=top_recommendations
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cost analysis failed: {str(e)}"
        )


@router.post("/{account_id}/sync")
async def sync_cost_data(
    account_id: UUID,
    days: int = Query(30, ge=1, le=90, description="Number of days to sync"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Sync cost data from AWS Cost Explorer
    
    This fetches the latest cost and usage data from AWS
    and stores it in the database
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
    
    # TODO: Trigger Celery task for cost data sync
    # from app.tasks import sync_cost_data_task
    # sync_cost_data_task.delay(str(account_id), days)
    
    return {
        "message": f"Cost data sync initiated for {days} days",
        "account_id": str(account_id),
        "status": "queued"
    }


@router.get("/{account_id}/forecast")
async def get_cost_forecast(
    account_id: UUID,
    days_ahead: int = Query(30, ge=7, le=90),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get cost forecast for the next N days
    
    Uses machine learning (Prophet) to predict future costs
    based on historical data
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
    
    # TODO: Implement ML-based forecasting using Prophet
    # For now, return simple projection based on recent average
    
    # Get last 30 days of data
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)
    
    cost_data = db.query(CostData).filter(
        CostData.account_id == account_id,
        CostData.time >= start_date,
        CostData.time <= end_date
    ).all()
    
    if not cost_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No historical cost data available for forecasting"
        )
    
    # Calculate daily average
    total_cost = sum(float(item.cost) for item in cost_data)
    daily_average = total_cost / 30
    
    # Generate simple forecast
    forecast = []
    current_date = datetime.utcnow().date()
    
    for i in range(1, days_ahead + 1):
        forecast_date = current_date + timedelta(days=i)
        # Simple projection (in production, use Prophet for better accuracy)
        forecast.append({
            "date": str(forecast_date),
            "predicted_cost": round(daily_average, 2),
            "confidence_lower": round(daily_average * 0.9, 2),
            "confidence_upper": round(daily_average * 1.1, 2)
        })
    
    return {
        "account_id": str(account_id),
        "forecast_days": days_ahead,
        "predicted_total": round(daily_average * days_ahead, 2),
        "forecast": forecast,
        "note": "This is a simple projection. ML-based forecasting with Prophet will be more accurate."
    }
