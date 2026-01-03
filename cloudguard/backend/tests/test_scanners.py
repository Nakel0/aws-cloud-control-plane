"""
Scanner Tests for CloudGuard
Uses moto for AWS mocking
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta

from app.core.aws_client import AWSClientManager
from app.modules.cost.scanner import CostScanner
from app.modules.security.scanner import SecurityScanner
from app.modules.reliability.scanner import ReliabilityScanner


@pytest.fixture
def mock_aws():
    """Create a mocked AWS client manager"""
    aws = MagicMock(spec=AWSClientManager)
    aws.settings = MagicMock()
    aws.settings.aws_region = "us-east-1"
    aws.settings.idle_resource_days = 7
    aws.settings.low_utilization_threshold = 10.0
    return aws


class TestCostScanner:
    """Test cost scanner functionality"""
    
    @pytest.mark.asyncio
    async def test_scan_idle_ec2_finds_idle_instance(self, mock_aws):
        """Test that idle EC2 instances are detected"""
        # Mock EC2 describe_instances
        mock_aws.ec2.describe_instances.return_value = {
            "Reservations": [{
                "Instances": [{
                    "InstanceId": "i-12345678",
                    "InstanceType": "m5.large",
                    "Tags": [{"Key": "Name", "Value": "test-instance"}],
                    "LaunchTime": datetime.utcnow() - timedelta(days=30),
                    "OwnerId": "123456789012",
                }]
            }]
        }
        
        # Mock CloudWatch metrics (low CPU)
        mock_aws.cloudwatch.get_metric_statistics.return_value = {
            "Datapoints": [
                {"Average": 2.5, "Maximum": 5.0},
                {"Average": 3.0, "Maximum": 6.0},
            ]
        }
        
        scanner = CostScanner(mock_aws)
        await scanner._scan_idle_ec2_instances(mock_aws, "us-east-1")
        
        assert len(scanner.findings) == 1
        finding = scanner.findings[0]
        assert "i-12345678" in finding.finding_id
        assert finding.severity.value in ["medium", "high"]
    
    @pytest.mark.asyncio
    async def test_scan_unattached_ebs(self, mock_aws):
        """Test that unattached EBS volumes are detected"""
        mock_aws.ec2.describe_volumes.return_value = {
            "Volumes": [{
                "VolumeId": "vol-12345678",
                "Size": 100,
                "VolumeType": "gp3",
                "State": "available",
                "CreateTime": datetime.utcnow() - timedelta(days=30),
                "Tags": [],
            }]
        }
        
        scanner = CostScanner(mock_aws)
        await scanner._scan_unattached_ebs_volumes(mock_aws, "us-east-1")
        
        assert len(scanner.findings) == 1
        finding = scanner.findings[0]
        assert finding.waste_type == "unattached"
        assert finding.estimated_savings > 0


class TestSecurityScanner:
    """Test security scanner functionality"""
    
    @pytest.mark.asyncio
    async def test_scan_open_security_group(self, mock_aws):
        """Test that open security groups are detected"""
        mock_aws.ec2.describe_security_groups.return_value = {
            "SecurityGroups": [{
                "GroupId": "sg-12345678",
                "GroupName": "test-sg",
                "OwnerId": "123456789012",
                "IpPermissions": [{
                    "FromPort": 22,
                    "ToPort": 22,
                    "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                }],
                "Tags": [],
            }]
        }
        
        scanner = SecurityScanner(mock_aws)
        await scanner._scan_open_security_groups(mock_aws, "us-east-1")
        
        assert len(scanner.findings) == 1
        finding = scanner.findings[0]
        assert finding.severity.value == "critical"
        assert 22 in finding.exposed_ports
    
    @pytest.mark.asyncio
    async def test_scan_unencrypted_ebs(self, mock_aws):
        """Test that unencrypted EBS volumes are detected"""
        mock_aws.ec2.describe_volumes.return_value = {
            "Volumes": [{
                "VolumeId": "vol-12345678",
                "Size": 100,
                "Encrypted": False,
                "CreateTime": datetime.utcnow(),
                "Tags": [],
            }]
        }
        
        scanner = SecurityScanner(mock_aws)
        await scanner._scan_unencrypted_ebs_volumes(mock_aws, "us-east-1")
        
        assert len(scanner.findings) == 1
        finding = scanner.findings[0]
        assert finding.encryption_type == "at_rest"


class TestReliabilityScanner:
    """Test reliability scanner functionality"""
    
    @pytest.mark.asyncio
    async def test_scan_single_az_rds(self, mock_aws):
        """Test that single-AZ RDS instances are detected"""
        mock_aws.rds.describe_db_instances.return_value = {
            "DBInstances": [{
                "DBInstanceIdentifier": "mydb",
                "DBInstanceClass": "db.m5.large",
                "AvailabilityZone": "us-east-1a",
                "MultiAZ": False,
                "DBInstanceStatus": "available",
            }]
        }
        
        scanner = ReliabilityScanner(mock_aws)
        await scanner._scan_single_az_rds(mock_aws, "us-east-1")
        
        assert len(scanner.findings) == 1
        finding = scanner.findings[0]
        assert finding.current_az == "us-east-1a"
        assert finding.severity.value == "high"
    
    @pytest.mark.asyncio
    async def test_scan_rds_no_backup(self, mock_aws):
        """Test that RDS without backups is detected"""
        mock_aws.rds.describe_db_instances.return_value = {
            "DBInstances": [{
                "DBInstanceIdentifier": "mydb",
                "DBInstanceClass": "db.m5.large",
                "BackupRetentionPeriod": 0,
                "AllocatedStorage": 100,
                "InstanceCreateTime": datetime.utcnow() - timedelta(days=30),
            }]
        }
        
        scanner = ReliabilityScanner(mock_aws)
        await scanner._scan_rds_no_backup(mock_aws, "us-east-1")
        
        assert len(scanner.findings) == 1
        finding = scanner.findings[0]
        assert finding.severity.value == "critical"
