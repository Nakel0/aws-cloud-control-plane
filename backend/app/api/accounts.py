"""
AWS Account Management API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import Account, AccountStatus
from app.services.aws_client import AWSClient

router = APIRouter()


class AccountCreate(BaseModel):
    """Schema for creating a new account"""
    aws_account_id: str = Field(..., min_length=12, max_length=12, description="12-digit AWS account ID")
    aws_account_name: str = Field(..., min_length=1, max_length=255, description="Friendly name for the account")
    role_arn: str = Field(..., description="ARN of the IAM role to assume")
    external_id: Optional[str] = Field(None, description="External ID for additional security")
    tags: Optional[dict] = Field(default_factory=dict, description="Custom tags")


class AccountResponse(BaseModel):
    """Schema for account response"""
    id: str
    customer_id: str
    aws_account_id: str
    aws_account_name: Optional[str]
    status: str
    status_message: Optional[str]
    last_scan_at: Optional[str]
    created_at: str
    tags: dict

    class Config:
        from_attributes = True


class AccountUpdate(BaseModel):
    """Schema for updating an account"""
    aws_account_name: Optional[str] = None
    role_arn: Optional[str] = None
    external_id: Optional[str] = None
    tags: Optional[dict] = None


@router.get("/", response_model=List[AccountResponse])
async def list_accounts(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    List all AWS accounts for the current user
    
    Returns a list of all connected AWS accounts with their current status
    """
    customer_id = current_user.get("sub")
    
    accounts = db.query(Account).filter(
        Account.customer_id == customer_id
    ).order_by(Account.created_at.desc()).all()
    
    return [account.to_dict() for account in accounts]


@router.post("/", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    account_data: AccountCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Add a new AWS account
    
    This endpoint:
    1. Validates AWS credentials by attempting to assume the role
    2. Creates a new account record
    3. Returns the account information
    """
    customer_id = current_user.get("sub")
    
    # Check if account already exists
    existing = db.query(Account).filter(
        Account.customer_id == customer_id,
        Account.aws_account_id == account_data.aws_account_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Account {account_data.aws_account_id} is already connected"
        )
    
    # Test AWS connection
    try:
        aws_client = AWSClient(account_data.role_arn, account_data.external_id)
        connection_test = aws_client.test_connection()
        
        if not connection_test["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to connect to AWS account: {connection_test.get('error')}"
            )
        
        # Verify the account ID matches
        if connection_test["account_id"] != account_data.aws_account_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Account ID mismatch. Expected {account_data.aws_account_id}, got {connection_test['account_id']}"
            )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"AWS authentication failed: {str(e)}"
        )
    
    # Create account record
    account = Account(
        customer_id=customer_id,
        aws_account_id=account_data.aws_account_id,
        aws_account_name=account_data.aws_account_name,
        role_arn=account_data.role_arn,
        external_id=account_data.external_id,
        status=AccountStatus.ACTIVE,
        status_message="Connection successful",
        tags=account_data.tags or {}
    )
    
    db.add(account)
    db.commit()
    db.refresh(account)
    
    # TODO: Trigger initial scan as background task
    # from app.tasks import scan_account
    # scan_account.delay(str(account.id))
    
    return account.to_dict()


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get detailed information about a specific AWS account"""
    customer_id = current_user.get("sub")
    
    account = db.query(Account).filter(
        Account.id == account_id,
        Account.customer_id == customer_id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account {account_id} not found"
        )
    
    return account.to_dict()


@router.patch("/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: UUID,
    account_update: AccountUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update an AWS account's configuration"""
    customer_id = current_user.get("sub")
    
    account = db.query(Account).filter(
        Account.id == account_id,
        Account.customer_id == customer_id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account {account_id} not found"
        )
    
    # Update fields
    if account_update.aws_account_name is not None:
        account.aws_account_name = account_update.aws_account_name
    
    if account_update.role_arn is not None:
        # Test new credentials if role_arn is being updated
        try:
            aws_client = AWSClient(
                account_update.role_arn,
                account_update.external_id or account.external_id
            )
            connection_test = aws_client.test_connection()
            
            if not connection_test["success"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to connect with new credentials: {connection_test.get('error')}"
                )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"AWS authentication failed: {str(e)}"
            )
        
        account.role_arn = account_update.role_arn
    
    if account_update.external_id is not None:
        account.external_id = account_update.external_id
    
    if account_update.tags is not None:
        account.tags = account_update.tags
    
    account.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(account)
    
    return account.to_dict()


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete an AWS account
    
    This will also delete all associated resources, findings, and recommendations
    """
    customer_id = current_user.get("sub")
    
    account = db.query(Account).filter(
        Account.id == account_id,
        Account.customer_id == customer_id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account {account_id} not found"
        )
    
    db.delete(account)
    db.commit()
    
    return None


@router.post("/{account_id}/scan")
async def trigger_scan(
    account_id: UUID,
    scan_type: Optional[str] = "full",
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Trigger a scan of the AWS account
    
    Scan types:
    - full: Complete scan (cost, security, resources)
    - cost: Cost analysis only
    - security: Security scan only
    - resources: Resource discovery only
    """
    customer_id = current_user.get("sub")
    
    account = db.query(Account).filter(
        Account.id == account_id,
        Account.customer_id == customer_id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account {account_id} not found"
        )
    
    # TODO: Trigger Celery task for scanning
    # from app.tasks import scan_account_full, scan_account_cost, scan_account_security
    # 
    # if scan_type == "full":
    #     scan_account_full.delay(str(account_id))
    # elif scan_type == "cost":
    #     scan_account_cost.delay(str(account_id))
    # elif scan_type == "security":
    #     scan_account_security.delay(str(account_id))
    
    return {
        "message": f"Scan initiated for account {account.aws_account_name}",
        "account_id": str(account_id),
        "scan_type": scan_type,
        "status": "queued"
    }


@router.post("/{account_id}/test-connection")
async def test_connection(
    account_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Test AWS connection for an account"""
    customer_id = current_user.get("sub")
    
    account = db.query(Account).filter(
        Account.id == account_id,
        Account.customer_id == customer_id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account {account_id} not found"
        )
    
    try:
        aws_client = AWSClient(account.role_arn, account.external_id)
        connection_test = aws_client.test_connection()
        
        if connection_test["success"]:
            account.status = AccountStatus.ACTIVE
            account.status_message = "Connection successful"
        else:
            account.status = AccountStatus.ERROR
            account.status_message = connection_test.get("error", "Connection failed")
        
        db.commit()
        
        return {
            "success": connection_test["success"],
            "account_id": connection_test.get("account_id"),
            "message": account.status_message
        }
    
    except Exception as e:
        account.status = AccountStatus.ERROR
        account.status_message = str(e)
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Connection test failed: {str(e)}"
        )
