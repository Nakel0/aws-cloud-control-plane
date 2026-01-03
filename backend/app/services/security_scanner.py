"""
Security Scanner Service
Scans AWS resources for security misconfigurations and compliance violations
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from app.services.aws_client import AWSClient
from app.models import SecurityFinding, Severity, FindingStatus

logger = logging.getLogger(__name__)


class SecurityScanner:
    """
    AWS Security Scanner
    
    Implements 100+ security checks across:
    - IAM Security
    - Network Security
    - Data Protection
    - Logging & Monitoring
    - Compute Security
    """
    
    def __init__(self, aws_client: AWSClient):
        self.aws_client = aws_client
        self.findings = []
    
    def run_full_scan(self) -> List[Dict[str, Any]]:
        """
        Run all security checks
        
        Returns:
            List of security findings
        """
        self.findings = []
        
        logger.info("Starting full security scan...")
        
        # IAM Checks
        self.check_iam_security()
        
        # Network Checks
        self.check_security_groups()
        self.check_s3_buckets()
        
        # Encryption Checks
        self.check_ebs_encryption()
        self.check_rds_encryption()
        
        # Logging Checks
        self.check_cloudtrail()
        self.check_vpc_flow_logs()
        
        logger.info(f"Security scan completed. Found {len(self.findings)} findings.")
        return self.findings
    
    # ==================== IAM Security Checks ====================
    
    def check_iam_security(self):
        """Check IAM security configurations"""
        self._check_root_account_access_keys()
        self._check_mfa_enabled()
        self._check_access_key_rotation()
        self._check_password_policy()
    
    def _check_root_account_access_keys(self):
        """Check if root account has access keys"""
        try:
            iam = self.aws_client.get_client('iam')
            
            # Get account summary
            summary = iam.get_account_summary()
            root_access_keys = summary['SummaryMap'].get('AccountAccessKeysPresent', 0)
            
            if root_access_keys > 0:
                self.findings.append({
                    'check_id': 'CIS-1.1',
                    'check_name': 'Root Account Access Keys',
                    'title': 'Root account has active access keys',
                    'description': 'The root account should not have active access keys. Use IAM users instead.',
                    'severity': Severity.CRITICAL,
                    'resource_id': 'root-account',
                    'resource_type': 'iam_root',
                    'remediation': 'Delete root account access keys and use IAM users for daily tasks.',
                    'compliance_frameworks': ['CIS', 'PCI-DSS', 'HIPAA'],
                    'compliance_controls': ['CIS 1.1', 'PCI 7.1', 'HIPAA 164.308(a)(3)'],
                    'evidence': {
                        'access_keys_present': root_access_keys
                    },
                    'can_auto_remediate': False  # Too risky
                })
        except Exception as e:
            logger.error(f"Failed to check root account access keys: {e}")
    
    def _check_mfa_enabled(self):
        """Check if MFA is enabled for IAM users"""
        try:
            iam = self.aws_client.get_client('iam')
            
            # Get all users
            paginator = iam.get_paginator('list_users')
            for page in paginator.paginate():
                for user in page['Users']:
                    username = user['UserName']
                    
                    # Check if MFA devices are assigned
                    mfa_devices = iam.list_mfa_devices(UserName=username)
                    
                    if not mfa_devices['MFADevices']:
                        # Check if user has console access
                        try:
                            login_profile = iam.get_login_profile(UserName=username)
                            
                            # User has console access but no MFA
                            self.findings.append({
                                'check_id': 'CIS-1.2',
                                'check_name': 'MFA Not Enabled',
                                'title': f'MFA not enabled for user: {username}',
                                'description': 'IAM user with console access does not have MFA enabled.',
                                'severity': Severity.HIGH,
                                'resource_id': user['Arn'],
                                'resource_type': 'iam_user',
                                'remediation': f'Enable MFA for user {username}.',
                                'compliance_frameworks': ['CIS', 'PCI-DSS', 'SOC2'],
                                'compliance_controls': ['CIS 1.2', 'PCI 8.3'],
                                'evidence': {
                                    'username': username,
                                    'mfa_devices': 0,
                                    'console_access': True
                                },
                                'can_auto_remediate': False  # Requires user action
                            })
                        except iam.exceptions.NoSuchEntityException:
                            # User doesn't have console access, skip
                            pass
        except Exception as e:
            logger.error(f"Failed to check MFA status: {e}")
    
    def _check_access_key_rotation(self):
        """Check if access keys are rotated regularly"""
        try:
            iam = self.aws_client.get_client('iam')
            
            # Get all users
            paginator = iam.get_paginator('list_users')
            for page in paginator.paginate():
                for user in page['Users']:
                    username = user['UserName']
                    
                    # Get access keys
                    keys = iam.list_access_keys(UserName=username)
                    
                    for key in keys['AccessKeyMetadata']:
                        create_date = key['CreateDate']
                        age_days = (datetime.now(create_date.tzinfo) - create_date).days
                        
                        # Flag keys older than 90 days
                        if age_days > 90:
                            self.findings.append({
                                'check_id': 'CIS-1.3',
                                'check_name': 'Access Key Rotation',
                                'title': f'Old access key for user: {username}',
                                'description': f'Access key has not been rotated in {age_days} days.',
                                'severity': Severity.MEDIUM,
                                'resource_id': key['AccessKeyId'],
                                'resource_type': 'iam_access_key',
                                'remediation': 'Rotate the access key and update applications.',
                                'compliance_frameworks': ['CIS', 'PCI-DSS'],
                                'compliance_controls': ['CIS 1.3', 'PCI 8.2.4'],
                                'evidence': {
                                    'username': username,
                                    'access_key_id': key['AccessKeyId'],
                                    'age_days': age_days,
                                    'created': create_date.isoformat()
                                },
                                'can_auto_remediate': True  # Can deactivate after notification
                            })
        except Exception as e:
            logger.error(f"Failed to check access key rotation: {e}")
    
    def _check_password_policy(self):
        """Check IAM password policy strength"""
        try:
            iam = self.aws_client.get_client('iam')
            
            try:
                policy = iam.get_account_password_policy()['PasswordPolicy']
            except iam.exceptions.NoSuchEntityException:
                # No password policy set
                self.findings.append({
                    'check_id': 'CIS-1.4',
                    'check_name': 'Password Policy',
                    'title': 'No IAM password policy configured',
                    'description': 'Account does not have a password policy configured.',
                    'severity': Severity.HIGH,
                    'resource_id': 'account-password-policy',
                    'resource_type': 'iam_policy',
                    'remediation': 'Configure a strong password policy.',
                    'compliance_frameworks': ['CIS', 'PCI-DSS', 'HIPAA'],
                    'compliance_controls': ['CIS 1.4-1.11', 'PCI 8.2'],
                    'evidence': {
                        'policy_exists': False
                    },
                    'can_auto_remediate': True
                })
                return
            
            # Check policy requirements
            requirements = {
                'minimum_password_length': (14, 'Minimum password length should be 14+'),
                'require_uppercase_characters': (True, 'Should require uppercase characters'),
                'require_lowercase_characters': (True, 'Should require lowercase characters'),
                'require_numbers': (True, 'Should require numbers'),
                'require_symbols': (True, 'Should require symbols'),
                'max_password_age': (90, 'Password should expire within 90 days'),
                'password_reuse_prevention': (24, 'Should prevent reuse of last 24 passwords')
            }
            
            for key, (expected, message) in requirements.items():
                actual = policy.get(key, 0 if isinstance(expected, int) else False)
                
                if isinstance(expected, int):
                    if actual < expected:
                        self.findings.append({
                            'check_id': f'CIS-1.{key}',
                            'check_name': 'Weak Password Policy',
                            'title': f'Password policy: {message}',
                            'description': f'Current value: {actual}, Expected: {expected}',
                            'severity': Severity.MEDIUM,
                            'resource_id': 'account-password-policy',
                            'resource_type': 'iam_policy',
                            'remediation': f'Update password policy: {message}',
                            'compliance_frameworks': ['CIS', 'PCI-DSS'],
                            'compliance_controls': ['CIS 1.4-1.11'],
                            'evidence': {
                                'setting': key,
                                'current': actual,
                                'expected': expected
                            },
                            'can_auto_remediate': True
                        })
                elif actual != expected:
                    self.findings.append({
                        'check_id': f'CIS-1.{key}',
                        'check_name': 'Weak Password Policy',
                        'title': f'Password policy: {message}',
                        'description': f'Current value: {actual}, Expected: {expected}',
                        'severity': Severity.MEDIUM,
                        'resource_id': 'account-password-policy',
                        'resource_type': 'iam_policy',
                        'remediation': f'Update password policy: {message}',
                        'compliance_frameworks': ['CIS'],
                        'compliance_controls': ['CIS 1.4-1.11'],
                        'evidence': {
                            'setting': key,
                            'current': actual,
                            'expected': expected
                        },
                        'can_auto_remediate': True
                    })
        except Exception as e:
            logger.error(f"Failed to check password policy: {e}")
    
    # ==================== Network Security Checks ====================
    
    def check_security_groups(self):
        """Check security group configurations"""
        try:
            ec2 = self.aws_client.get_client('ec2')
            
            # Get all security groups
            response = ec2.describe_security_groups()
            
            for sg in response['SecurityGroups']:
                sg_id = sg['GroupId']
                sg_name = sg['GroupName']
                
                # Check for overly permissive rules
                for rule in sg.get('IpPermissions', []):
                    from_port = rule.get('FromPort', 0)
                    to_port = rule.get('ToPort', 65535)
                    
                    # Check for 0.0.0.0/0 on sensitive ports
                    for ip_range in rule.get('IpRanges', []):
                        cidr = ip_range.get('CidrIp')
                        
                        if cidr == '0.0.0.0/0':
                            # Define sensitive ports
                            sensitive_ports = {
                                22: 'SSH',
                                3389: 'RDP',
                                3306: 'MySQL',
                                5432: 'PostgreSQL',
                                1433: 'MSSQL',
                                27017: 'MongoDB',
                                6379: 'Redis'
                            }
                            
                            for port, service in sensitive_ports.items():
                                if from_port <= port <= to_port:
                                    self.findings.append({
                                        'check_id': 'SEC-SG-001',
                                        'check_name': 'Overly Permissive Security Group',
                                        'title': f'Security group allows public access to {service}',
                                        'description': f'{sg_name} ({sg_id}) allows 0.0.0.0/0 access to port {port} ({service})',
                                        'severity': Severity.CRITICAL,
                                        'resource_id': sg_id,
                                        'resource_type': 'security_group',
                                        'remediation': f'Restrict access to {service} port to specific IP addresses only.',
                                        'compliance_frameworks': ['CIS', 'PCI-DSS', 'HIPAA'],
                                        'compliance_controls': ['CIS 4.1', 'PCI 1.2.1'],
                                        'evidence': {
                                            'security_group': sg_id,
                                            'group_name': sg_name,
                                            'port': port,
                                            'service': service,
                                            'cidr': cidr
                                        },
                                        'can_auto_remediate': True  # Can remove the rule
                                    })
        except Exception as e:
            logger.error(f"Failed to check security groups: {e}")
    
    def check_s3_buckets(self):
        """Check S3 bucket security"""
        try:
            s3 = self.aws_client.get_client('s3')
            
            # List all buckets
            buckets = s3.list_buckets()
            
            for bucket in buckets['Buckets']:
                bucket_name = bucket['Name']
                
                # Check public access block configuration
                try:
                    public_access = s3.get_public_access_block(Bucket=bucket_name)
                    config = public_access['PublicAccessBlockConfiguration']
                    
                    if not all([
                        config.get('BlockPublicAcls'),
                        config.get('BlockPublicPolicy'),
                        config.get('IgnorePublicAcls'),
                        config.get('RestrictPublicBuckets')
                    ]):
                        self.findings.append({
                            'check_id': 'SEC-S3-001',
                            'check_name': 'S3 Public Access',
                            'title': f'S3 bucket may allow public access: {bucket_name}',
                            'description': 'Bucket does not have all public access blocks enabled.',
                            'severity': Severity.HIGH,
                            'resource_id': bucket_name,
                            'resource_type': 's3_bucket',
                            'remediation': 'Enable all S3 public access blocks.',
                            'compliance_frameworks': ['CIS', 'PCI-DSS', 'HIPAA'],
                            'compliance_controls': ['CIS 2.1.1', 'PCI 1.2.1'],
                            'evidence': {
                                'bucket': bucket_name,
                                'public_access_config': config
                            },
                            'can_auto_remediate': True
                        })
                except s3.exceptions.NoSuchPublicAccessBlockConfiguration:
                    # No public access block configured
                    self.findings.append({
                        'check_id': 'SEC-S3-001',
                        'check_name': 'S3 Public Access Block Not Configured',
                        'title': f'S3 bucket has no public access block: {bucket_name}',
                        'description': 'Bucket does not have public access block configuration.',
                        'severity': Severity.HIGH,
                        'resource_id': bucket_name,
                        'resource_type': 's3_bucket',
                        'remediation': 'Configure S3 public access blocks.',
                        'compliance_frameworks': ['CIS', 'HIPAA'],
                        'compliance_controls': ['CIS 2.1.1'],
                        'evidence': {
                            'bucket': bucket_name,
                            'public_access_config': None
                        },
                        'can_auto_remediate': True
                    })
                
                # Check encryption
                try:
                    encryption = s3.get_bucket_encryption(Bucket=bucket_name)
                except s3.exceptions.ServerSideEncryptionConfigurationNotFoundError:
                    self.findings.append({
                        'check_id': 'SEC-S3-002',
                        'check_name': 'S3 Encryption Not Enabled',
                        'title': f'S3 bucket not encrypted: {bucket_name}',
                        'description': 'Bucket does not have default encryption enabled.',
                        'severity': Severity.HIGH,
                        'resource_id': bucket_name,
                        'resource_type': 's3_bucket',
                        'remediation': 'Enable default encryption (AES-256 or KMS).',
                        'compliance_frameworks': ['PCI-DSS', 'HIPAA', 'SOC2'],
                        'compliance_controls': ['PCI 3.4', 'HIPAA 164.312(a)(2)(iv)'],
                        'evidence': {
                            'bucket': bucket_name,
                            'encryption': None
                        },
                        'can_auto_remediate': True
                    })
        except Exception as e:
            logger.error(f"Failed to check S3 buckets: {e}")
    
    # ==================== Encryption Checks ====================
    
    def check_ebs_encryption(self):
        """Check if EBS volumes are encrypted"""
        try:
            ec2 = self.aws_client.get_client('ec2')
            
            # Get all volumes
            response = ec2.describe_volumes()
            
            for volume in response['Volumes']:
                volume_id = volume['VolumeId']
                encrypted = volume.get('Encrypted', False)
                
                if not encrypted:
                    self.findings.append({
                        'check_id': 'SEC-EBS-001',
                        'check_name': 'Unencrypted EBS Volume',
                        'title': f'EBS volume not encrypted: {volume_id}',
                        'description': 'EBS volume does not have encryption enabled.',
                        'severity': Severity.HIGH,
                        'resource_id': volume_id,
                        'resource_type': 'ebs_volume',
                        'remediation': 'Create encrypted snapshot and replace volume.',
                        'compliance_frameworks': ['PCI-DSS', 'HIPAA', 'SOC2'],
                        'compliance_controls': ['PCI 3.4', 'HIPAA 164.312(a)(2)(iv)'],
                        'evidence': {
                            'volume_id': volume_id,
                            'encrypted': encrypted,
                            'size_gb': volume['Size'],
                            'state': volume['State']
                        },
                        'can_auto_remediate': False  # Requires downtime
                    })
        except Exception as e:
            logger.error(f"Failed to check EBS encryption: {e}")
    
    def check_rds_encryption(self):
        """Check if RDS instances are encrypted"""
        try:
            rds = self.aws_client.get_client('rds')
            
            # Get all RDS instances
            response = rds.describe_db_instances()
            
            for db in response['DBInstances']:
                db_id = db['DBInstanceIdentifier']
                encrypted = db.get('StorageEncrypted', False)
                
                if not encrypted:
                    self.findings.append({
                        'check_id': 'SEC-RDS-001',
                        'check_name': 'Unencrypted RDS Instance',
                        'title': f'RDS instance not encrypted: {db_id}',
                        'description': 'RDS instance does not have storage encryption enabled.',
                        'severity': Severity.CRITICAL,
                        'resource_id': db['DBInstanceArn'],
                        'resource_type': 'rds_instance',
                        'remediation': 'Create encrypted snapshot and restore to new instance.',
                        'compliance_frameworks': ['PCI-DSS', 'HIPAA', 'SOC2'],
                        'compliance_controls': ['PCI 3.4', 'HIPAA 164.312(a)(2)(iv)'],
                        'evidence': {
                            'db_instance': db_id,
                            'encrypted': encrypted,
                            'engine': db['Engine'],
                            'multi_az': db.get('MultiAZ', False)
                        },
                        'can_auto_remediate': False  # Requires careful planning
                    })
        except Exception as e:
            logger.error(f"Failed to check RDS encryption: {e}")
    
    # ==================== Logging Checks ====================
    
    def check_cloudtrail(self):
        """Check if CloudTrail is enabled"""
        try:
            cloudtrail = self.aws_client.get_client('cloudtrail')
            
            # Get trail status
            trails = cloudtrail.describe_trails()
            
            if not trails['trailList']:
                self.findings.append({
                    'check_id': 'CIS-2.1',
                    'check_name': 'CloudTrail Not Enabled',
                    'title': 'CloudTrail is not enabled',
                    'description': 'No CloudTrail trails are configured for this account.',
                    'severity': Severity.CRITICAL,
                    'resource_id': 'cloudtrail',
                    'resource_type': 'cloudtrail',
                    'remediation': 'Enable CloudTrail for all regions.',
                    'compliance_frameworks': ['CIS', 'PCI-DSS', 'HIPAA', 'SOC2'],
                    'compliance_controls': ['CIS 2.1', 'PCI 10.1', 'HIPAA 164.312(b)'],
                    'evidence': {
                        'trails_configured': 0
                    },
                    'can_auto_remediate': True
                })
            else:
                for trail in trails['trailList']:
                    trail_name = trail['Name']
                    status = cloudtrail.get_trail_status(Name=trail_name)
                    
                    if not status['IsLogging']:
                        self.findings.append({
                            'check_id': 'CIS-2.1',
                            'check_name': 'CloudTrail Not Logging',
                            'title': f'CloudTrail not actively logging: {trail_name}',
                            'description': 'CloudTrail trail exists but is not actively logging.',
                            'severity': Severity.HIGH,
                            'resource_id': trail['TrailARN'],
                            'resource_type': 'cloudtrail',
                            'remediation': 'Start CloudTrail logging.',
                            'compliance_frameworks': ['CIS', 'PCI-DSS', 'SOC2'],
                            'compliance_controls': ['CIS 2.1', 'PCI 10.1'],
                            'evidence': {
                                'trail_name': trail_name,
                                'is_logging': False
                            },
                            'can_auto_remediate': True
                        })
        except Exception as e:
            logger.error(f"Failed to check CloudTrail: {e}")
    
    def check_vpc_flow_logs(self):
        """Check if VPC Flow Logs are enabled"""
        try:
            ec2 = self.aws_client.get_client('ec2')
            
            # Get all VPCs
            vpcs = ec2.describe_vpcs()
            
            for vpc in vpcs['Vpcs']:
                vpc_id = vpc['VpcId']
                
                # Check for flow logs
                flow_logs = ec2.describe_flow_logs(
                    Filters=[{'Name': 'resource-id', 'Values': [vpc_id]}]
                )
                
                if not flow_logs['FlowLogs']:
                    self.findings.append({
                        'check_id': 'CIS-2.9',
                        'check_name': 'VPC Flow Logs Not Enabled',
                        'title': f'VPC Flow Logs not enabled: {vpc_id}',
                        'description': 'VPC does not have Flow Logs enabled.',
                        'severity': Severity.MEDIUM,
                        'resource_id': vpc_id,
                        'resource_type': 'vpc',
                        'remediation': 'Enable VPC Flow Logs.',
                        'compliance_frameworks': ['CIS', 'SOC2'],
                        'compliance_controls': ['CIS 2.9'],
                        'evidence': {
                            'vpc_id': vpc_id,
                            'flow_logs_enabled': False
                        },
                        'can_auto_remediate': True
                    })
        except Exception as e:
            logger.error(f"Failed to check VPC Flow Logs: {e}")
