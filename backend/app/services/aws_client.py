import boto3
from botocore.exceptions import ClientError
from fastapi import HTTPException

class AWSClientFactory:
    def __init__(self):
        self.sts_client = boto3.client('sts')

    def get_cross_account_session(self, role_arn: str, external_id: str):
        """
        Assume the customer's role and return a boto3 session.
        """
        try:
            assumed_role_object = self.sts_client.assume_role(
                RoleArn=role_arn,
                RoleSessionName="UnifiedPlatformSession",
                ExternalId=external_id
            )
            credentials = assumed_role_object['Credentials']

            return boto3.Session(
                aws_access_key_id=credentials['AccessKeyId'],
                aws_secret_access_key=credentials['SecretAccessKey'],
                aws_session_token=credentials['SessionToken'],
            )
        except ClientError as e:
            raise HTTPException(status_code=400, detail=f"Failed to assume role: {str(e)}")

    def verify_access(self, role_arn: str, external_id: str) -> bool:
        """
        Verify if the provided role credentials work.
        """
        session = self.get_cross_account_session(role_arn, external_id)
        # Try a simple call like sts.get_caller_identity to verify
        try:
            sts = session.client('sts')
            sts.get_caller_identity()
            return True
        except Exception:
            return False
