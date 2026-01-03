"""
AWS Client Manager - Centralized AWS API access
Handles credentials, session management, and multi-region support
"""

import boto3
from botocore.config import Config
from functools import lru_cache
from typing import Optional, Any
import structlog

from app.core.config import get_settings

logger = structlog.get_logger()


class AWSClientManager:
    """
    Manages AWS client connections with support for:
    - Multi-region operations
    - Assume role for cross-account access
    - Connection pooling and caching
    """
    
    def __init__(
        self,
        region: Optional[str] = None,
        assume_role_arn: Optional[str] = None,
    ):
        self.settings = get_settings()
        self.region = region or self.settings.aws_region
        self.assume_role_arn = assume_role_arn or self.settings.aws_assume_role_arn
        self._session: Optional[boto3.Session] = None
        self._clients: dict[str, Any] = {}
    
    def _get_session(self) -> boto3.Session:
        """Get or create boto3 session"""
        if self._session is None:
            session_kwargs = {"region_name": self.region}
            
            # Use explicit credentials if provided
            if self.settings.aws_access_key_id:
                session_kwargs["aws_access_key_id"] = self.settings.aws_access_key_id
                session_kwargs["aws_secret_access_key"] = self.settings.aws_secret_access_key
            
            self._session = boto3.Session(**session_kwargs)
            
            # Assume role if specified (for cross-account access)
            if self.assume_role_arn:
                sts = self._session.client("sts")
                response = sts.assume_role(
                    RoleArn=self.assume_role_arn,
                    RoleSessionName="CloudGuardSession",
                    DurationSeconds=3600,
                )
                credentials = response["Credentials"]
                self._session = boto3.Session(
                    aws_access_key_id=credentials["AccessKeyId"],
                    aws_secret_access_key=credentials["SecretAccessKey"],
                    aws_session_token=credentials["SessionToken"],
                    region_name=self.region,
                )
                logger.info("Assumed role successfully", role_arn=self.assume_role_arn)
        
        return self._session
    
    def get_client(self, service_name: str, region: Optional[str] = None) -> Any:
        """
        Get a boto3 client for the specified service
        
        Args:
            service_name: AWS service name (ec2, s3, rds, etc.)
            region: Optional region override
        
        Returns:
            boto3 client for the service
        """
        region = region or self.region
        cache_key = f"{service_name}:{region}"
        
        if cache_key not in self._clients:
            session = self._get_session()
            config = Config(
                retries={"max_attempts": 3, "mode": "adaptive"},
                max_pool_connections=25,
            )
            self._clients[cache_key] = session.client(
                service_name,
                region_name=region,
                config=config,
            )
            logger.debug("Created AWS client", service=service_name, region=region)
        
        return self._clients[cache_key]
    
    def get_resource(self, service_name: str, region: Optional[str] = None) -> Any:
        """Get a boto3 resource for the specified service"""
        region = region or self.region
        session = self._get_session()
        return session.resource(service_name, region_name=region)
    
    @staticmethod
    def get_all_regions() -> list[str]:
        """Get list of all available AWS regions"""
        ec2 = boto3.client("ec2", region_name="us-east-1")
        regions = ec2.describe_regions()["Regions"]
        return [r["RegionName"] for r in regions]
    
    # Convenience methods for common services
    @property
    def ec2(self):
        return self.get_client("ec2")
    
    @property
    def s3(self):
        return self.get_client("s3")
    
    @property
    def rds(self):
        return self.get_client("rds")
    
    @property
    def iam(self):
        return self.get_client("iam")
    
    @property
    def cloudwatch(self):
        return self.get_client("cloudwatch")
    
    @property
    def ce(self):
        """Cost Explorer client"""
        return self.get_client("ce", region="us-east-1")  # CE is global
    
    @property
    def config(self):
        """AWS Config client"""
        return self.get_client("config")
    
    @property
    def securityhub(self):
        return self.get_client("securityhub")
    
    @property
    def lambda_client(self):
        return self.get_client("lambda")
    
    @property
    def elbv2(self):
        return self.get_client("elbv2")
    
    @property
    def ebs(self):
        return self.get_client("ebs")


@lru_cache
def get_aws_client(region: Optional[str] = None) -> AWSClientManager:
    """Get cached AWS client manager instance"""
    return AWSClientManager(region=region)
