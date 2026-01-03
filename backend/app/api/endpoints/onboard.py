from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.aws_client import AWSClientFactory

router = APIRouter()

class AWSConnectRequest(BaseModel):
    account_id: str
    role_arn: str
    external_id: str

@router.post("/aws")
async def connect_aws_account(request: AWSConnectRequest):
    """
    Connect a customer AWS account using Cross-Account IAM Role.
    """
    client_factory = AWSClientFactory()
    
    # Verify we can assume the role
    is_valid = client_factory.verify_access(request.role_arn, request.external_id)
    
    if not is_valid:
        raise HTTPException(status_code=400, detail="Could not verify access with provided Role ARN and External ID.")

    # In a real app, save these credentials (encrypted) to the DB here.
    
    return {"status": "success", "message": f"Successfully connected to account {request.account_id}"}
