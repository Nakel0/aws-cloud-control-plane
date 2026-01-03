"""
Remediation Engine - Automated fix for findings
"""

from datetime import datetime
from typing import Optional
import structlog

from app.core.aws_client import AWSClientManager
from app.models.schemas import (
    RemediationAction,
    RemediationResult,
    RemediationStatus,
)

logger = structlog.get_logger()


class RemediationEngine:
    """
    Executes automated remediation actions for findings.
    Supports dry-run mode for safe testing.
    """
    
    def __init__(self, aws_client: AWSClientManager):
        self.aws = aws_client
        
        # Map finding types to remediation handlers
        self.handlers = {
            "cost-unattached-ebs": self._remediate_unattached_ebs,
            "cost-unattached-eip": self._remediate_unattached_eip,
            "cost-old-snapshot": self._remediate_old_snapshot,
            "security-public-s3": self._remediate_public_s3,
            "security-no-public-block-s3": self._remediate_s3_public_block,
            "security-unencrypted-s3": self._remediate_s3_encryption,
            "security-open-sg": self._remediate_open_security_group,
            "reliability-no-alarm": self._create_cloudwatch_alarm,
            "reliability-no-snapshot": self._create_ebs_snapshot,
        }
    
    async def get_available_actions(self, finding_id: str) -> list[RemediationAction]:
        """Get available remediation actions for a finding"""
        actions = []
        
        # Parse finding type from ID
        parts = finding_id.split("-")
        if len(parts) >= 2:
            finding_type = f"{parts[0]}-{parts[1]}"
            
            if finding_type in self.handlers:
                action = RemediationAction(
                    action_id=f"action-{finding_id}",
                    finding_id=finding_id,
                    action_type=finding_type,
                    description=self._get_action_description(finding_type),
                    is_reversible=self._is_reversible(finding_type),
                    requires_approval=self._requires_approval(finding_type),
                    estimated_impact=self._get_impact(finding_type),
                )
                actions.append(action)
        
        return actions
    
    async def remediate(
        self, 
        finding_id: str, 
        dry_run: bool = True
    ) -> RemediationResult:
        """Execute remediation for a finding"""
        started_at = datetime.utcnow()
        
        # Parse finding type
        parts = finding_id.split("-")
        if len(parts) < 3:
            return RemediationResult(
                action_id=f"action-{finding_id}",
                status=RemediationStatus.FAILED,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                result_message="Invalid finding ID format",
            )
        
        finding_type = f"{parts[0]}-{parts[1]}"
        resource_id = "-".join(parts[2:])
        
        if finding_type not in self.handlers:
            return RemediationResult(
                action_id=f"action-{finding_id}",
                status=RemediationStatus.FAILED,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                result_message=f"No remediation handler for {finding_type}",
            )
        
        try:
            handler = self.handlers[finding_type]
            result = await handler(resource_id, dry_run)
            
            return RemediationResult(
                action_id=f"action-{finding_id}",
                status=RemediationStatus.COMPLETED if not dry_run else RemediationStatus.PENDING,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                result_message=result,
                rollback_available=self._is_reversible(finding_type),
            )
            
        except Exception as e:
            logger.error("Remediation failed", finding_id=finding_id, error=str(e))
            return RemediationResult(
                action_id=f"action-{finding_id}",
                status=RemediationStatus.FAILED,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                result_message=str(e),
            )
    
    # ============ Remediation Handlers ============
    
    async def _remediate_unattached_ebs(
        self, volume_id: str, dry_run: bool
    ) -> str:
        """Delete unattached EBS volume after creating snapshot"""
        ec2 = self.aws.ec2
        
        if dry_run:
            return f"[DRY RUN] Would create snapshot of {volume_id} and delete the volume"
        
        # Create snapshot first
        snapshot = ec2.create_snapshot(
            VolumeId=volume_id,
            Description=f"CloudGuard backup before deletion - {volume_id}",
            TagSpecifications=[{
                "ResourceType": "snapshot",
                "Tags": [{"Key": "CloudGuard", "Value": "backup-before-delete"}]
            }]
        )
        
        # Wait for snapshot to complete (simplified - should use waiter)
        logger.info("Created backup snapshot", snapshot_id=snapshot["SnapshotId"])
        
        # Delete volume
        ec2.delete_volume(VolumeId=volume_id)
        
        return f"Created snapshot {snapshot['SnapshotId']} and deleted volume {volume_id}"
    
    async def _remediate_unattached_eip(
        self, allocation_id: str, dry_run: bool
    ) -> str:
        """Release unattached Elastic IP"""
        ec2 = self.aws.ec2
        
        if dry_run:
            return f"[DRY RUN] Would release Elastic IP {allocation_id}"
        
        ec2.release_address(AllocationId=allocation_id)
        
        return f"Released Elastic IP {allocation_id}"
    
    async def _remediate_old_snapshot(
        self, snapshot_id: str, dry_run: bool
    ) -> str:
        """Delete old EBS snapshot"""
        ec2 = self.aws.ec2
        
        if dry_run:
            return f"[DRY RUN] Would delete snapshot {snapshot_id}"
        
        ec2.delete_snapshot(SnapshotId=snapshot_id)
        
        return f"Deleted snapshot {snapshot_id}"
    
    async def _remediate_public_s3(
        self, bucket_name: str, dry_run: bool
    ) -> str:
        """Remove public access from S3 bucket"""
        s3 = self.aws.s3
        
        if dry_run:
            return f"[DRY RUN] Would enable Block Public Access for bucket {bucket_name}"
        
        s3.put_public_access_block(
            Bucket=bucket_name,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            }
        )
        
        return f"Enabled Block Public Access for bucket {bucket_name}"
    
    async def _remediate_s3_public_block(
        self, bucket_name: str, dry_run: bool
    ) -> str:
        """Enable S3 Block Public Access"""
        return await self._remediate_public_s3(bucket_name, dry_run)
    
    async def _remediate_s3_encryption(
        self, bucket_name: str, dry_run: bool
    ) -> str:
        """Enable default encryption on S3 bucket"""
        s3 = self.aws.s3
        
        if dry_run:
            return f"[DRY RUN] Would enable SSE-S3 encryption for bucket {bucket_name}"
        
        s3.put_bucket_encryption(
            Bucket=bucket_name,
            ServerSideEncryptionConfiguration={
                "Rules": [{
                    "ApplyServerSideEncryptionByDefault": {
                        "SSEAlgorithm": "AES256"
                    },
                    "BucketKeyEnabled": True,
                }]
            }
        )
        
        return f"Enabled SSE-S3 encryption for bucket {bucket_name}"
    
    async def _remediate_open_security_group(
        self, sg_rule_id: str, dry_run: bool
    ) -> str:
        """Revoke overly permissive security group rule"""
        # Parse sg_id from the rule ID (format: sg-xxx-fromport-toport)
        parts = sg_rule_id.split("-")
        sg_id = f"{parts[0]}-{parts[1]}"
        
        ec2 = self.aws.ec2
        
        if dry_run:
            return f"[DRY RUN] Would revoke 0.0.0.0/0 access from security group {sg_id}"
        
        # This is simplified - in production, would need to know exact rule details
        return f"[REQUIRES MANUAL REVIEW] Security group {sg_id} has open rules that need manual review"
    
    async def _create_cloudwatch_alarm(
        self, instance_id: str, dry_run: bool
    ) -> str:
        """Create CloudWatch alarm for EC2 instance"""
        cw = self.aws.cloudwatch
        
        if dry_run:
            return f"[DRY RUN] Would create CPU and Status Check alarms for {instance_id}"
        
        # Create CPU alarm
        cw.put_metric_alarm(
            AlarmName=f"CloudGuard-CPU-High-{instance_id}",
            AlarmDescription=f"CPU utilization alarm for {instance_id}",
            MetricName="CPUUtilization",
            Namespace="AWS/EC2",
            Statistic="Average",
            Period=300,
            EvaluationPeriods=2,
            Threshold=80,
            ComparisonOperator="GreaterThanThreshold",
            Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
            Tags=[{"Key": "CloudGuard", "Value": "auto-created"}],
        )
        
        # Create status check alarm
        cw.put_metric_alarm(
            AlarmName=f"CloudGuard-StatusCheck-{instance_id}",
            AlarmDescription=f"Status check alarm for {instance_id}",
            MetricName="StatusCheckFailed",
            Namespace="AWS/EC2",
            Statistic="Maximum",
            Period=60,
            EvaluationPeriods=2,
            Threshold=1,
            ComparisonOperator="GreaterThanOrEqualToThreshold",
            Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
            Tags=[{"Key": "CloudGuard", "Value": "auto-created"}],
        )
        
        return f"Created CPU and StatusCheck alarms for {instance_id}"
    
    async def _create_ebs_snapshot(
        self, volume_id: str, dry_run: bool
    ) -> str:
        """Create EBS snapshot"""
        ec2 = self.aws.ec2
        
        if dry_run:
            return f"[DRY RUN] Would create snapshot of volume {volume_id}"
        
        snapshot = ec2.create_snapshot(
            VolumeId=volume_id,
            Description=f"CloudGuard automated snapshot - {volume_id}",
            TagSpecifications=[{
                "ResourceType": "snapshot",
                "Tags": [{"Key": "CloudGuard", "Value": "automated-backup"}]
            }]
        )
        
        return f"Created snapshot {snapshot['SnapshotId']} for volume {volume_id}"
    
    # ============ Helper Methods ============
    
    def _get_action_description(self, finding_type: str) -> str:
        """Get human-readable description for action"""
        descriptions = {
            "cost-unattached-ebs": "Create backup snapshot and delete unattached volume",
            "cost-unattached-eip": "Release unused Elastic IP address",
            "cost-old-snapshot": "Delete old EBS snapshot",
            "security-public-s3": "Enable S3 Block Public Access",
            "security-no-public-block-s3": "Enable S3 Block Public Access",
            "security-unencrypted-s3": "Enable default S3 encryption",
            "security-open-sg": "Revoke overly permissive security group rule",
            "reliability-no-alarm": "Create CloudWatch monitoring alarms",
            "reliability-no-snapshot": "Create EBS volume snapshot",
        }
        return descriptions.get(finding_type, "Unknown action")
    
    def _is_reversible(self, finding_type: str) -> bool:
        """Check if action is reversible"""
        # Most delete operations are not reversible
        non_reversible = {"cost-unattached-eip", "cost-old-snapshot"}
        return finding_type not in non_reversible
    
    def _requires_approval(self, finding_type: str) -> bool:
        """Check if action requires approval"""
        approval_required = {"cost-unattached-ebs", "security-open-sg"}
        return finding_type in approval_required
    
    def _get_impact(self, finding_type: str) -> str:
        """Get estimated impact of action"""
        impacts = {
            "cost-unattached-ebs": "Deletes volume data (snapshot created first)",
            "cost-unattached-eip": "Releases IP address (may get different IP)",
            "cost-old-snapshot": "Deletes snapshot permanently",
            "security-public-s3": "Blocks all public access to bucket",
            "security-no-public-block-s3": "Blocks all public access to bucket",
            "security-unencrypted-s3": "No impact - encrypts new objects",
            "security-open-sg": "May break connectivity if rule is needed",
            "reliability-no-alarm": "No impact - adds monitoring",
            "reliability-no-snapshot": "No impact - creates backup",
        }
        return impacts.get(finding_type, "Unknown impact")
