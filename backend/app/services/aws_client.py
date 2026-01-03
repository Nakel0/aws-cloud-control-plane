"""
AWS Client wrapper for cross-account access
"""
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class AWSClient:
    """
    AWS Client for cross-account access using IAM roles
    
    Handles credential management and session creation for accessing
    customer AWS accounts via AssumeRole
    """
    
    def __init__(self, role_arn: str, external_id: Optional[str] = None, region: str = None):
        """
        Initialize AWS client with cross-account role
        
        Args:
            role_arn: ARN of the IAM role to assume
            external_id: External ID for additional security
            region: AWS region (defaults to config)
        """
        self.role_arn = role_arn
        self.external_id = external_id
        self.region = region or settings.AWS_DEFAULT_REGION
        self._session = None
        self._session_expiry = None
        
    def _get_session(self) -> boto3.Session:
        """
        Get or create AWS session with assumed role credentials
        
        Sessions are cached and refreshed when expired
        """
        # Return cached session if still valid
        if self._session and self._session_expiry:
            if datetime.utcnow() < self._session_expiry:
                return self._session
        
        try:
            # Create STS client
            sts = boto3.client('sts', region_name=self.region)
            
            # Assume role parameters
            assume_role_params = {
                'RoleArn': self.role_arn,
                'RoleSessionName': f'cloudguard-{datetime.utcnow().strftime("%Y%m%d%H%M%S")}',
                'DurationSeconds': 3600  # 1 hour
            }
            
            if self.external_id:
                assume_role_params['ExternalId'] = self.external_id
            
            # Assume the role
            response = sts.assume_role(**assume_role_params)
            
            # Extract credentials
            credentials = response['Credentials']
            
            # Create session with temporary credentials
            self._session = boto3.Session(
                aws_access_key_id=credentials['AccessKeyId'],
                aws_secret_access_key=credentials['SecretAccessKey'],
                aws_session_token=credentials['SessionToken'],
                region_name=self.region
            )
            
            # Set expiry (5 minutes before actual expiry for safety)
            self._session_expiry = credentials['Expiration'] - timedelta(minutes=5)
            
            logger.info(f"Successfully assumed role: {self.role_arn}")
            return self._session
            
        except (ClientError, BotoCoreError) as e:
            logger.error(f"Failed to assume role {self.role_arn}: {e}")
            raise
    
    def get_client(self, service_name: str, region: str = None):
        """
        Get boto3 client for specified service
        
        Args:
            service_name: AWS service name (e.g., 'ec2', 'rds', 's3')
            region: Override default region
        
        Returns:
            boto3 client object
        """
        session = self._get_session()
        return session.client(service_name, region_name=region or self.region)
    
    def get_resource(self, service_name: str, region: str = None):
        """
        Get boto3 resource for specified service
        
        Args:
            service_name: AWS service name (e.g., 'ec2', 's3')
            region: Override default region
        
        Returns:
            boto3 resource object
        """
        session = self._get_session()
        return session.resource(service_name, region_name=region or self.region)
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test AWS connection and permissions
        
        Returns:
            Dict with connection status and account info
        """
        try:
            session = self._get_session()
            sts = session.client('sts')
            identity = sts.get_caller_identity()
            
            return {
                "success": True,
                "account_id": identity['Account'],
                "user_arn": identity['Arn'],
                "user_id": identity['UserId']
            }
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_regions(self, service: str = 'ec2') -> list:
        """
        Get list of available AWS regions for a service
        
        Args:
            service: AWS service name
        
        Returns:
            List of region names
        """
        try:
            session = self._get_session()
            ec2 = session.client('ec2', region_name='us-east-1')
            regions = ec2.describe_regions()
            return [region['RegionName'] for region in regions['Regions']]
        except Exception as e:
            logger.error(f"Failed to get regions: {e}")
            return []
