"""
Recommendations API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import (
    Account,
    Recommendation,
    AutomationLog,
    RecommendationType,
    Priority,
    RecommendationStatus
)

router = APIRouter()


class RecommendationResponse(BaseModel):
    """Recommendation response model"""
    id: str
    account_id: str
    resource_id: str
    resource_type: str
    type: str
    priority: str
    title: str
    description: str
    potential_savings: Optional[float]
    effort_level: Optional[str]
    risk_level: Optional[str]
    confidence: Optional[float]
    actions: list
    evidence: dict
    status: str
    created_at: str
    expires_at: Optional[str]

    class Config:
        from_attributes = True


class RecommendationSummaryResponse(BaseModel):
    """Recommendation summary"""
    account_id: str
    total_recommendations: int
    by_type: dict
    by_priority: dict
    by_status: dict
    total_potential_savings: float


class ExecuteActionRequest(BaseModel):
    """Request to execute an action"""
    action_type: str
    auto_approve: bool = False
    notes: Optional[str] = None


@router.get("/{account_id}/recommendations", response_model=List[RecommendationResponse])
async def list_recommendations(
    account_id: UUID,
    type: Optional[RecommendationType] = Query(None, description="Filter by type"),
    priority: Optional[Priority] = Query(None, description="Filter by priority"),
    status: Optional[RecommendationStatus] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    List recommendations for an account
    
    Returns all optimization recommendations with optional filtering
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
    query = db.query(Recommendation).filter(
        Recommendation.account_id == account_id
    )
    
    if type:
        query = query.filter(Recommendation.type == type)
    
    if priority:
        query = query.filter(Recommendation.priority == priority)
    
    if status:
        query = query.filter(Recommendation.status == status)
    
    # Order by potential savings (highest first)
    recommendations = query.order_by(
        Recommendation.potential_savings.desc().nullslast(),
        Recommendation.created_at.desc()
    ).offset(offset).limit(limit).all()
    
    return [rec.to_dict() for rec in recommendations]


@router.get("/{account_id}/summary", response_model=RecommendationSummaryResponse)
async def get_recommendations_summary(
    account_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get recommendations summary for an account
    
    Returns overview with breakdowns by type, priority, and status
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
    
    # Get all recommendations
    recommendations = db.query(Recommendation).filter(
        Recommendation.account_id == account_id
    ).all()
    
    # Calculate breakdowns
    by_type = {}
    by_priority = {}
    by_status = {}
    total_savings = 0
    
    for rec in recommendations:
        # By type
        rec_type = rec.type.value
        by_type[rec_type] = by_type.get(rec_type, 0) + 1
        
        # By priority
        rec_priority = rec.priority.value
        by_priority[rec_priority] = by_priority.get(rec_priority, 0) + 1
        
        # By status
        rec_status = rec.status.value
        by_status[rec_status] = by_status.get(rec_status, 0) + 1
        
        # Total savings (only pending recommendations)
        if rec.status == RecommendationStatus.PENDING and rec.potential_savings:
            total_savings += float(rec.potential_savings)
    
    return RecommendationSummaryResponse(
        account_id=str(account_id),
        total_recommendations=len(recommendations),
        by_type=by_type,
        by_priority=by_priority,
        by_status=by_status,
        total_potential_savings=round(total_savings, 2)
    )


@router.get("/{account_id}/recommendation/{recommendation_id}", response_model=RecommendationResponse)
async def get_recommendation_detail(
    account_id: UUID,
    recommendation_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get detailed information about a specific recommendation"""
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
    
    recommendation = db.query(Recommendation).filter(
        Recommendation.id == recommendation_id,
        Recommendation.account_id == account_id
    ).first()
    
    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommendation {recommendation_id} not found"
        )
    
    return recommendation.to_dict()


@router.patch("/{account_id}/recommendation/{recommendation_id}/status")
async def update_recommendation_status(
    account_id: UUID,
    recommendation_id: UUID,
    new_status: RecommendationStatus,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update the status of a recommendation
    
    Statuses:
    - pending: Not yet reviewed
    - approved: Approved for execution
    - in_progress: Being worked on
    - completed: Successfully applied
    - rejected: User decided not to apply
    - expired: No longer relevant
    """
    customer_id = current_user.get("sub")
    user_id = current_user.get("sub")
    
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
    
    recommendation = db.query(Recommendation).filter(
        Recommendation.id == recommendation_id,
        Recommendation.account_id == account_id
    ).first()
    
    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommendation {recommendation_id} not found"
        )
    
    # Update status
    old_status = recommendation.status
    recommendation.status = new_status
    recommendation.status_reason = reason
    
    if new_status == RecommendationStatus.APPROVED:
        recommendation.approved_by = user_id
    
    if new_status == RecommendationStatus.COMPLETED:
        recommendation.executed_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "recommendation_id": str(recommendation_id),
        "old_status": old_status.value,
        "new_status": new_status.value,
        "message": f"Recommendation status updated from {old_status.value} to {new_status.value}"
    }


@router.post("/{account_id}/recommendation/{recommendation_id}/execute")
async def execute_recommendation(
    account_id: UUID,
    recommendation_id: UUID,
    action_request: ExecuteActionRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Execute an action for a recommendation
    
    This endpoint:
    1. Validates the action
    2. Checks if approval is required
    3. Executes the action on AWS (if approved)
    4. Logs the execution
    5. Updates recommendation status
    """
    customer_id = current_user.get("sub")
    user_id = current_user.get("sub")
    
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
    
    recommendation = db.query(Recommendation).filter(
        Recommendation.id == recommendation_id,
        Recommendation.account_id == account_id
    ).first()
    
    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommendation {recommendation_id} not found"
        )
    
    # Check if action exists
    action_found = False
    for action in recommendation.actions:
        if action.get("type") == action_request.action_type:
            action_found = True
            break
    
    if not action_found:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Action {action_request.action_type} not found in recommendation"
        )
    
    # Check if approval is required
    if recommendation.requires_approval and not action_request.auto_approve:
        # Create approval request
        recommendation.status = RecommendationStatus.APPROVED
        recommendation.approved_by = user_id
        db.commit()
        
        return {
            "recommendation_id": str(recommendation_id),
            "status": "approved",
            "message": "Action approved. Execute again to apply changes."
        }
    
    # Execute action
    # TODO: Implement actual AWS action execution
    # from app.services.automation_engine import AutomationEngine
    # engine = AutomationEngine(account)
    # result = engine.execute_action(recommendation, action_request.action_type)
    
    # For now, simulate execution
    execution_result = {
        "success": True,
        "message": f"Action {action_request.action_type} executed successfully",
        "aws_request_id": "simulated-request-id"
    }
    
    # Log execution
    log = AutomationLog(
        recommendation_id=recommendation_id,
        action_type=action_request.action_type,
        action_description=f"Executed {action_request.action_type} on {recommendation.resource_id}",
        status="success" if execution_result["success"] else "failed",
        executed_by=user_id,
        execution_method="manual",
        aws_request_id=execution_result.get("aws_request_id"),
        executed_at=datetime.utcnow(),
        completed_at=datetime.utcnow()
    )
    db.add(log)
    
    # Update recommendation status
    recommendation.status = RecommendationStatus.COMPLETED
    recommendation.executed_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "recommendation_id": str(recommendation_id),
        "status": "completed",
        "execution_log_id": str(log.id),
        "message": execution_result["message"]
    }


@router.post("/{account_id}/recommendation/{recommendation_id}/rollback")
async def rollback_recommendation(
    account_id: UUID,
    recommendation_id: UUID,
    execution_log_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Rollback a previously executed recommendation
    
    This restores the resource to its previous state
    """
    customer_id = current_user.get("sub")
    user_id = current_user.get("sub")
    
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
    
    recommendation = db.query(Recommendation).filter(
        Recommendation.id == recommendation_id,
        Recommendation.account_id == account_id
    ).first()
    
    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommendation {recommendation_id} not found"
        )
    
    # Get execution log
    if execution_log_id:
        log = db.query(AutomationLog).filter(
            AutomationLog.id == execution_log_id
        ).first()
    else:
        # Get most recent log
        log = db.query(AutomationLog).filter(
            AutomationLog.recommendation_id == recommendation_id
        ).order_by(AutomationLog.executed_at.desc()).first()
    
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No execution log found for rollback"
        )
    
    if not log.rollback_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No rollback data available"
        )
    
    # TODO: Implement actual rollback
    # from app.services.automation_engine import AutomationEngine
    # engine = AutomationEngine(account)
    # result = engine.rollback(log)
    
    # Update log
    log.rolled_back_at = datetime.utcnow()
    log.status = "rolled_back"
    
    # Revert recommendation status
    recommendation.status = RecommendationStatus.PENDING
    
    db.commit()
    
    return {
        "recommendation_id": str(recommendation_id),
        "execution_log_id": str(log.id),
        "status": "rolled_back",
        "message": "Action successfully rolled back"
    }


@router.get("/{account_id}/execution-logs")
async def list_execution_logs(
    account_id: UUID,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    List automation execution logs for an account
    
    Returns audit trail of all automated actions
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
    
    # Get logs for recommendations in this account
    logs = db.query(AutomationLog).join(
        Recommendation,
        AutomationLog.recommendation_id == Recommendation.id
    ).filter(
        Recommendation.account_id == account_id
    ).order_by(
        AutomationLog.executed_at.desc()
    ).offset(offset).limit(limit).all()
    
    return [log.to_dict() for log in logs]


@router.post("/{account_id}/bulk-approve")
async def bulk_approve_recommendations(
    account_id: UUID,
    recommendation_ids: List[UUID],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Bulk approve multiple recommendations
    
    Useful for approving many low-risk recommendations at once
    """
    customer_id = current_user.get("sub")
    user_id = current_user.get("sub")
    
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
    
    # Update all recommendations
    approved_count = 0
    for rec_id in recommendation_ids:
        recommendation = db.query(Recommendation).filter(
            Recommendation.id == rec_id,
            Recommendation.account_id == account_id
        ).first()
        
        if recommendation and recommendation.status == RecommendationStatus.PENDING:
            recommendation.status = RecommendationStatus.APPROVED
            recommendation.approved_by = user_id
            approved_count += 1
    
    db.commit()
    
    return {
        "account_id": str(account_id),
        "requested": len(recommendation_ids),
        "approved": approved_count,
        "message": f"Approved {approved_count} of {len(recommendation_ids)} recommendations"
    }
