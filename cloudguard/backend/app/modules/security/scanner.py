"""
Security Scanner - Detects AWS security misconfigurations
"""

from datetime import datetime, timedelta
from typing import Optional
import structlog

from app.core.aws_client import AWSClientManager
from app.core.config import get_settings
from app.models.schemas import (
    ResourceType,
    ResourceBase,
    Severity,
    SecurityFinding,
    PublicAccessFinding,
    EncryptionFinding,
    IAMFinding,
)

logger = structlog.get_logger()


class SecurityScanner:
    """
    Scans AWS resources for security misconfigurations:
    - Public S3 buckets
    - Open security groups
    - Unencrypted resources
    - IAM issues (overly permissive policies, unused credentials)
    - Missing MFA
    - Root account usage
    """
    
    def __init__(self, aws_client: AWSClientManager):
        self.aws = aws_client
        self.settings = get_settings()
        self.findings: list[SecurityFinding] = []
    
    async def scan_all(self, regions: Optional[list[str]] = None) -> list[SecurityFinding]:
        """Run all security scans"""
        regions = regions or [self.settings.aws_region]
        self.findings = []
        
        # Global scans (IAM, S3)
        await self._scan_public_s3_buckets()
        await self._scan_iam_users()
        await self._scan_iam_policies()
        await self._scan_root_account()
        
        # Regional scans
        for region in regions:
            logger.info("Scanning region for security issues", region=region)
            regional_aws = AWSClientManager(region=region)
            
            await self._scan_open_security_groups(regional_aws, region)
            await self._scan_unencrypted_ebs_volumes(regional_aws, region)
            await self._scan_unencrypted_rds_instances(regional_aws, region)
            await self._scan_public_rds_instances(regional_aws, region)
            await self._scan_default_vpcs(regional_aws, region)
            await self._scan_unrestricted_nacls(regional_aws, region)
        
        logger.info("Security scan completed", findings_count=len(self.findings))
        return self.findings
    
    async def _scan_public_s3_buckets(self) -> None:
        """Find S3 buckets with public access"""
        try:
            s3 = self.aws.s3
            
            buckets = s3.list_buckets().get("Buckets", [])
            
            for bucket in buckets:
                bucket_name = bucket["Name"]
                
                try:
                    # Check bucket public access block
                    try:
                        public_access = s3.get_public_access_block(Bucket=bucket_name)
                        config = public_access.get("PublicAccessBlockConfiguration", {})
                        
                        # If all blocks are not enabled, bucket might be public
                        if not all([
                            config.get("BlockPublicAcls", False),
                            config.get("IgnorePublicAcls", False),
                            config.get("BlockPublicPolicy", False),
                            config.get("RestrictPublicBuckets", False),
                        ]):
                            # Check ACL for public access
                            acl = s3.get_bucket_acl(Bucket=bucket_name)
                            for grant in acl.get("Grants", []):
                                grantee = grant.get("Grantee", {})
                                if grantee.get("URI") in [
                                    "http://acs.amazonaws.com/groups/global/AllUsers",
                                    "http://acs.amazonaws.com/groups/global/AuthenticatedUsers",
                                ]:
                                    finding = PublicAccessFinding(
                                        finding_id=f"security-public-s3-{bucket_name}",
                                        severity=Severity.CRITICAL,
                                        title=f"Public S3 Bucket: {bucket_name}",
                                        description=f"S3 bucket {bucket_name} allows public access via ACL.",
                                        resource=ResourceBase(
                                            resource_id=bucket_name,
                                            resource_type=ResourceType.S3_BUCKET,
                                            resource_name=bucket_name,
                                            region="global",
                                            account_id="",
                                            tags={},
                                            created_at=bucket.get("CreationDate"),
                                        ),
                                        recommendation="Enable S3 Block Public Access settings and review bucket ACL.",
                                        remediation_available=True,
                                        compliance_frameworks=["CIS AWS 2.1.1", "SOC2", "PCI-DSS"],
                                        public_access_type="s3_bucket_acl",
                                        exposed_to="internet",
                                    )
                                    self.findings.append(finding)
                                    break
                                    
                    except s3.exceptions.NoSuchPublicAccessBlockConfiguration:
                        # No public access block = potentially public
                        finding = PublicAccessFinding(
                            finding_id=f"security-no-public-block-s3-{bucket_name}",
                            severity=Severity.HIGH,
                            title=f"S3 Bucket Missing Public Access Block: {bucket_name}",
                            description=f"S3 bucket {bucket_name} does not have S3 Block Public Access enabled.",
                            resource=ResourceBase(
                                resource_id=bucket_name,
                                resource_type=ResourceType.S3_BUCKET,
                                resource_name=bucket_name,
                                region="global",
                                account_id="",
                                tags={},
                            ),
                            recommendation="Enable S3 Block Public Access for this bucket.",
                            remediation_available=True,
                            compliance_frameworks=["CIS AWS 2.1.2"],
                            public_access_type="missing_block",
                            exposed_to="potentially_public",
                        )
                        self.findings.append(finding)
                        
                    # Check bucket encryption
                    try:
                        s3.get_bucket_encryption(Bucket=bucket_name)
                    except Exception as enc_error:
                        if "ServerSideEncryptionConfigurationNotFoundError" in str(enc_error):
                            finding = EncryptionFinding(
                                finding_id=f"security-unencrypted-s3-{bucket_name}",
                                severity=Severity.HIGH,
                                title=f"Unencrypted S3 Bucket: {bucket_name}",
                                description=f"S3 bucket {bucket_name} does not have default encryption enabled.",
                                resource=ResourceBase(
                                    resource_id=bucket_name,
                                    resource_type=ResourceType.S3_BUCKET,
                                    resource_name=bucket_name,
                                    region="global",
                                    account_id="",
                                    tags={},
                                ),
                                recommendation="Enable default encryption (SSE-S3 or SSE-KMS) for this bucket.",
                                remediation_available=True,
                                compliance_frameworks=["CIS AWS 2.1.1", "SOC2", "HIPAA"],
                                encryption_type="at_rest",
                            )
                            self.findings.append(finding)
                            
                except Exception as bucket_error:
                    logger.warning("Error scanning bucket", bucket=bucket_name, error=str(bucket_error))
                    
        except Exception as e:
            logger.error("Error scanning S3 buckets", error=str(e))
    
    async def _scan_open_security_groups(
        self, aws: AWSClientManager, region: str
    ) -> None:
        """Find security groups with overly permissive rules"""
        try:
            ec2 = aws.ec2
            
            response = ec2.describe_security_groups()
            
            dangerous_ports = [22, 3389, 3306, 5432, 1433, 27017, 6379, 9200, 11211]
            
            for sg in response.get("SecurityGroups", []):
                sg_id = sg["GroupId"]
                sg_name = sg["GroupName"]
                
                # Skip default VPC security group
                if sg_name == "default":
                    continue
                
                for rule in sg.get("IpPermissions", []):
                    from_port = rule.get("FromPort", 0)
                    to_port = rule.get("ToPort", 65535)
                    
                    for ip_range in rule.get("IpRanges", []):
                        cidr = ip_range.get("CidrIp", "")
                        
                        # Check for 0.0.0.0/0 (open to the world)
                        if cidr == "0.0.0.0/0":
                            # Check if it exposes dangerous ports
                            exposed_ports = [
                                p for p in dangerous_ports
                                if from_port <= p <= to_port
                            ]
                            
                            if exposed_ports or from_port == 0:
                                severity = Severity.CRITICAL if exposed_ports else Severity.HIGH
                                
                                finding = PublicAccessFinding(
                                    finding_id=f"security-open-sg-{sg_id}-{from_port}-{to_port}",
                                    severity=severity,
                                    title=f"Open Security Group: {sg_name}",
                                    description=f"Security group {sg_name} ({sg_id}) allows inbound traffic from 0.0.0.0/0 on ports {from_port}-{to_port}.",
                                    resource=ResourceBase(
                                        resource_id=sg_id,
                                        resource_type=ResourceType.SECURITY_GROUP,
                                        resource_name=sg_name,
                                        region=region,
                                        account_id=sg.get("OwnerId", ""),
                                        tags=self._tags_to_dict(sg.get("Tags", [])),
                                    ),
                                    recommendation=f"Restrict inbound access to specific IP ranges or security groups. Exposed ports: {exposed_ports or 'all'}",
                                    remediation_available=True,
                                    compliance_frameworks=["CIS AWS 5.1", "SOC2", "PCI-DSS"],
                                    public_access_type="security_group",
                                    exposed_ports=exposed_ports if exposed_ports else list(range(from_port, to_port + 1))[:10],
                                    exposed_to="0.0.0.0/0",
                                )
                                self.findings.append(finding)
                                
        except Exception as e:
            logger.error("Error scanning security groups", error=str(e), region=region)
    
    async def _scan_unencrypted_ebs_volumes(
        self, aws: AWSClientManager, region: str
    ) -> None:
        """Find unencrypted EBS volumes"""
        try:
            ec2 = aws.ec2
            
            response = ec2.describe_volumes()
            
            for volume in response.get("Volumes", []):
                if not volume.get("Encrypted", False):
                    volume_id = volume["VolumeId"]
                    size_gb = volume["Size"]
                    
                    finding = EncryptionFinding(
                        finding_id=f"security-unencrypted-ebs-{volume_id}",
                        severity=Severity.HIGH,
                        title=f"Unencrypted EBS Volume: {volume_id}",
                        description=f"EBS volume {volume_id} ({size_gb}GB) is not encrypted.",
                        resource=ResourceBase(
                            resource_id=volume_id,
                            resource_type=ResourceType.EBS_VOLUME,
                            resource_name=self._get_name_tag(volume.get("Tags", [])),
                            region=region,
                            account_id="",
                            tags=self._tags_to_dict(volume.get("Tags", [])),
                            created_at=volume.get("CreateTime"),
                        ),
                        recommendation="Create an encrypted snapshot and restore to a new encrypted volume.",
                        remediation_available=True,
                        compliance_frameworks=["CIS AWS 2.2.1", "SOC2", "HIPAA", "PCI-DSS"],
                        encryption_type="at_rest",
                    )
                    self.findings.append(finding)
                    
        except Exception as e:
            logger.error("Error scanning EBS volumes", error=str(e), region=region)
    
    async def _scan_unencrypted_rds_instances(
        self, aws: AWSClientManager, region: str
    ) -> None:
        """Find unencrypted RDS instances"""
        try:
            rds = aws.rds
            
            response = rds.describe_db_instances()
            
            for db in response.get("DBInstances", []):
                if not db.get("StorageEncrypted", False):
                    db_id = db["DBInstanceIdentifier"]
                    
                    finding = EncryptionFinding(
                        finding_id=f"security-unencrypted-rds-{db_id}",
                        severity=Severity.CRITICAL,
                        title=f"Unencrypted RDS Instance: {db_id}",
                        description=f"RDS instance {db_id} does not have storage encryption enabled.",
                        resource=ResourceBase(
                            resource_id=db_id,
                            resource_type=ResourceType.RDS_INSTANCE,
                            resource_name=db_id,
                            region=region,
                            account_id="",
                            tags={},
                        ),
                        recommendation="Enable encryption by creating an encrypted snapshot and restoring to a new instance.",
                        remediation_available=False,  # Requires manual migration
                        compliance_frameworks=["CIS AWS 2.3.1", "SOC2", "HIPAA", "PCI-DSS"],
                        encryption_type="at_rest",
                        data_classification="database",
                    )
                    self.findings.append(finding)
                    
        except Exception as e:
            logger.error("Error scanning RDS instances", error=str(e), region=region)
    
    async def _scan_public_rds_instances(
        self, aws: AWSClientManager, region: str
    ) -> None:
        """Find publicly accessible RDS instances"""
        try:
            rds = aws.rds
            
            response = rds.describe_db_instances()
            
            for db in response.get("DBInstances", []):
                if db.get("PubliclyAccessible", False):
                    db_id = db["DBInstanceIdentifier"]
                    
                    finding = PublicAccessFinding(
                        finding_id=f"security-public-rds-{db_id}",
                        severity=Severity.CRITICAL,
                        title=f"Publicly Accessible RDS: {db_id}",
                        description=f"RDS instance {db_id} is publicly accessible from the internet.",
                        resource=ResourceBase(
                            resource_id=db_id,
                            resource_type=ResourceType.RDS_INSTANCE,
                            resource_name=db_id,
                            region=region,
                            account_id="",
                            tags={},
                        ),
                        recommendation="Disable public accessibility and use VPC security groups.",
                        remediation_available=True,
                        compliance_frameworks=["CIS AWS 2.3.2", "SOC2", "PCI-DSS"],
                        public_access_type="rds_public",
                        exposed_ports=[db.get("Endpoint", {}).get("Port", 3306)],
                        exposed_to="internet",
                    )
                    self.findings.append(finding)
                    
        except Exception as e:
            logger.error("Error scanning public RDS", error=str(e), region=region)
    
    async def _scan_iam_users(self) -> None:
        """Scan IAM users for security issues"""
        try:
            iam = self.aws.iam
            
            users = iam.list_users().get("Users", [])
            
            for user in users:
                username = user["UserName"]
                user_arn = user["Arn"]
                
                # Check for MFA
                mfa_devices = iam.list_mfa_devices(UserName=username).get("MFADevices", [])
                
                if not mfa_devices:
                    # Check if user has console access
                    try:
                        iam.get_login_profile(UserName=username)
                        # User has console access but no MFA
                        finding = IAMFinding(
                            finding_id=f"security-no-mfa-{username}",
                            severity=Severity.HIGH,
                            title=f"IAM User Without MFA: {username}",
                            description=f"IAM user {username} has console access but MFA is not enabled.",
                            resource=ResourceBase(
                                resource_id=user_arn,
                                resource_type=ResourceType.IAM_USER,
                                resource_name=username,
                                region="global",
                                account_id="",
                                tags={},
                                created_at=user.get("CreateDate"),
                            ),
                            recommendation="Enable MFA for this IAM user.",
                            remediation_available=False,  # Requires user action
                            compliance_frameworks=["CIS AWS 1.10", "SOC2", "PCI-DSS"],
                            iam_issue_type="no_mfa",
                        )
                        self.findings.append(finding)
                    except iam.exceptions.NoSuchEntityException:
                        # No console access, MFA not required
                        pass
                
                # Check for unused access keys
                access_keys = iam.list_access_keys(UserName=username).get("AccessKeyMetadata", [])
                
                for key in access_keys:
                    key_id = key["AccessKeyId"]
                    
                    try:
                        last_used = iam.get_access_key_last_used(AccessKeyId=key_id)
                        last_used_date = last_used.get("AccessKeyLastUsed", {}).get("LastUsedDate")
                        
                        if last_used_date:
                            days_unused = (datetime.utcnow().replace(tzinfo=last_used_date.tzinfo) - last_used_date).days
                            
                            if days_unused > 90:
                                finding = IAMFinding(
                                    finding_id=f"security-unused-key-{key_id}",
                                    severity=Severity.MEDIUM,
                                    title=f"Unused Access Key: {key_id}",
                                    description=f"Access key {key_id} for user {username} hasn't been used in {days_unused} days.",
                                    resource=ResourceBase(
                                        resource_id=key_id,
                                        resource_type=ResourceType.IAM_USER,
                                        resource_name=username,
                                        region="global",
                                        account_id="",
                                        tags={},
                                    ),
                                    recommendation="Deactivate or delete this unused access key.",
                                    remediation_available=True,
                                    compliance_frameworks=["CIS AWS 1.12"],
                                    iam_issue_type="unused_credentials",
                                    last_used=last_used_date,
                                )
                                self.findings.append(finding)
                                
                    except Exception as key_error:
                        logger.warning("Error checking access key", key_id=key_id, error=str(key_error))
                        
        except Exception as e:
            logger.error("Error scanning IAM users", error=str(e))
    
    async def _scan_iam_policies(self) -> None:
        """Scan for overly permissive IAM policies"""
        try:
            iam = self.aws.iam
            
            # Check for policies with Admin access
            policies = iam.list_policies(Scope="Local").get("Policies", [])
            
            for policy in policies:
                policy_arn = policy["Arn"]
                policy_name = policy["PolicyName"]
                
                # Get default version
                version_id = policy["DefaultVersionId"]
                
                try:
                    policy_doc = iam.get_policy_version(
                        PolicyArn=policy_arn,
                        VersionId=version_id
                    )["PolicyVersion"]["Document"]
                    
                    # Check for overly permissive statements
                    statements = policy_doc.get("Statement", [])
                    if isinstance(statements, dict):
                        statements = [statements]
                    
                    for statement in statements:
                        effect = statement.get("Effect", "")
                        action = statement.get("Action", "")
                        resource = statement.get("Resource", "")
                        
                        # Check for Admin-like access
                        if effect == "Allow":
                            if (action == "*" or action == ["*"]) and (resource == "*" or resource == ["*"]):
                                finding = IAMFinding(
                                    finding_id=f"security-admin-policy-{policy_name}",
                                    severity=Severity.HIGH,
                                    title=f"Overly Permissive Policy: {policy_name}",
                                    description=f"Policy {policy_name} grants full admin access (*:*).",
                                    resource=ResourceBase(
                                        resource_id=policy_arn,
                                        resource_type=ResourceType.IAM_ROLE,
                                        resource_name=policy_name,
                                        region="global",
                                        account_id="",
                                        tags={},
                                    ),
                                    recommendation="Apply least privilege principle - grant only necessary permissions.",
                                    remediation_available=False,
                                    compliance_frameworks=["CIS AWS 1.16", "SOC2"],
                                    iam_issue_type="overly_permissive",
                                    affected_permissions=["*:*"],
                                )
                                self.findings.append(finding)
                                break
                                
                except Exception as policy_error:
                    logger.warning("Error checking policy", policy=policy_name, error=str(policy_error))
                    
        except Exception as e:
            logger.error("Error scanning IAM policies", error=str(e))
    
    async def _scan_root_account(self) -> None:
        """Check root account security"""
        try:
            iam = self.aws.iam
            
            # Get account summary
            summary = iam.get_account_summary().get("SummaryMap", {})
            
            # Check if root has access keys
            if summary.get("AccountAccessKeysPresent", 0) > 0:
                finding = IAMFinding(
                    finding_id="security-root-access-keys",
                    severity=Severity.CRITICAL,
                    title="Root Account Has Access Keys",
                    description="The root account has active access keys. This is a critical security risk.",
                    resource=ResourceBase(
                        resource_id="root",
                        resource_type=ResourceType.IAM_USER,
                        resource_name="root",
                        region="global",
                        account_id="",
                        tags={},
                    ),
                    recommendation="Delete root access keys and use IAM users instead.",
                    remediation_available=False,
                    compliance_frameworks=["CIS AWS 1.4", "SOC2", "PCI-DSS"],
                    iam_issue_type="root_access_keys",
                )
                self.findings.append(finding)
            
            # Check if root has MFA
            if summary.get("AccountMFAEnabled", 0) == 0:
                finding = IAMFinding(
                    finding_id="security-root-no-mfa",
                    severity=Severity.CRITICAL,
                    title="Root Account MFA Not Enabled",
                    description="The root account does not have MFA enabled. This is a critical security risk.",
                    resource=ResourceBase(
                        resource_id="root",
                        resource_type=ResourceType.IAM_USER,
                        resource_name="root",
                        region="global",
                        account_id="",
                        tags={},
                    ),
                    recommendation="Enable MFA on the root account immediately.",
                    remediation_available=False,
                    compliance_frameworks=["CIS AWS 1.5", "SOC2", "PCI-DSS"],
                    iam_issue_type="root_no_mfa",
                )
                self.findings.append(finding)
                
        except Exception as e:
            logger.error("Error scanning root account", error=str(e))
    
    async def _scan_default_vpcs(
        self, aws: AWSClientManager, region: str
    ) -> None:
        """Check for resources in default VPC"""
        try:
            ec2 = aws.ec2
            
            # Find default VPC
            vpcs = ec2.describe_vpcs(Filters=[{"Name": "is-default", "Values": ["true"]}])
            
            for vpc in vpcs.get("Vpcs", []):
                vpc_id = vpc["VpcId"]
                
                # Check if there are resources in default VPC
                instances = ec2.describe_instances(
                    Filters=[
                        {"Name": "vpc-id", "Values": [vpc_id]},
                        {"Name": "instance-state-name", "Values": ["running", "stopped"]},
                    ]
                )
                
                instance_count = sum(
                    len(r.get("Instances", []))
                    for r in instances.get("Reservations", [])
                )
                
                if instance_count > 0:
                    finding = SecurityFinding(
                        finding_id=f"security-default-vpc-{vpc_id}",
                        severity=Severity.MEDIUM,
                        title=f"Resources in Default VPC: {vpc_id}",
                        description=f"Found {instance_count} EC2 instances running in the default VPC.",
                        resource=ResourceBase(
                            resource_id=vpc_id,
                            resource_type=ResourceType.EC2_INSTANCE,
                            resource_name="default-vpc",
                            region=region,
                            account_id="",
                            tags={},
                        ),
                        recommendation="Use custom VPCs with proper network segmentation.",
                        remediation_available=False,
                        compliance_frameworks=["CIS AWS 4.1"],
                    )
                    self.findings.append(finding)
                    
        except Exception as e:
            logger.error("Error scanning default VPCs", error=str(e), region=region)
    
    async def _scan_unrestricted_nacls(
        self, aws: AWSClientManager, region: str
    ) -> None:
        """Check for overly permissive Network ACLs"""
        try:
            ec2 = aws.ec2
            
            nacls = ec2.describe_network_acls().get("NetworkAcls", [])
            
            for nacl in nacls:
                nacl_id = nacl["NetworkAclId"]
                
                for entry in nacl.get("Entries", []):
                    # Check inbound rules
                    if not entry.get("Egress", True):  # Inbound
                        cidr = entry.get("CidrBlock", "")
                        rule_action = entry.get("RuleAction", "")
                        
                        # Allow all from 0.0.0.0/0
                        if cidr == "0.0.0.0/0" and rule_action == "allow":
                            protocol = entry.get("Protocol", "-1")
                            
                            if protocol == "-1":  # All traffic
                                finding = PublicAccessFinding(
                                    finding_id=f"security-open-nacl-{nacl_id}",
                                    severity=Severity.MEDIUM,
                                    title=f"Unrestricted Network ACL: {nacl_id}",
                                    description=f"Network ACL {nacl_id} allows all inbound traffic from 0.0.0.0/0.",
                                    resource=ResourceBase(
                                        resource_id=nacl_id,
                                        resource_type=ResourceType.SECURITY_GROUP,
                                        resource_name=nacl_id,
                                        region=region,
                                        account_id="",
                                        tags=self._tags_to_dict(nacl.get("Tags", [])),
                                    ),
                                    recommendation="Restrict Network ACL rules to specific IP ranges and ports.",
                                    remediation_available=True,
                                    compliance_frameworks=["CIS AWS 5.1"],
                                    public_access_type="nacl",
                                    exposed_to="0.0.0.0/0",
                                )
                                self.findings.append(finding)
                                break
                                
        except Exception as e:
            logger.error("Error scanning NACLs", error=str(e), region=region)
    
    # ============ Helper Methods ============
    
    def _get_name_tag(self, tags: list) -> Optional[str]:
        """Extract Name tag from tag list"""
        for tag in tags:
            if tag.get("Key") == "Name":
                return tag.get("Value")
        return None
    
    def _tags_to_dict(self, tags: list) -> dict[str, str]:
        """Convert AWS tag list to dictionary"""
        return {tag["Key"]: tag["Value"] for tag in tags}
