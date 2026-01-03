"""
Reliability Scanner - Detects AWS reliability and resilience issues
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
    ReliabilityFinding,
    SingleAZFinding,
    NoBackupFinding,
    NoAutoScalingFinding,
    HealthCheckFinding,
)

logger = structlog.get_logger()


class ReliabilityScanner:
    """
    Scans AWS resources for reliability issues:
    - Single AZ deployments
    - Missing backups
    - No auto-scaling
    - Missing health checks
    - No monitoring/alarms
    """
    
    def __init__(self, aws_client: AWSClientManager):
        self.aws = aws_client
        self.settings = get_settings()
        self.findings: list[ReliabilityFinding] = []
    
    async def scan_all(self, regions: Optional[list[str]] = None) -> list[ReliabilityFinding]:
        """Run all reliability scans"""
        regions = regions or [self.settings.aws_region]
        self.findings = []
        
        for region in regions:
            logger.info("Scanning region for reliability issues", region=region)
            regional_aws = AWSClientManager(region=region)
            
            await self._scan_single_az_rds(regional_aws, region)
            await self._scan_rds_no_backup(regional_aws, region)
            await self._scan_single_az_elb(regional_aws, region)
            await self._scan_ec2_no_autoscaling(regional_aws, region)
            await self._scan_missing_cloudwatch_alarms(regional_aws, region)
            await self._scan_elb_health_checks(regional_aws, region)
            await self._scan_ebs_no_snapshots(regional_aws, region)
        
        logger.info("Reliability scan completed", findings_count=len(self.findings))
        return self.findings
    
    async def _scan_single_az_rds(
        self, aws: AWSClientManager, region: str
    ) -> None:
        """Find RDS instances without Multi-AZ"""
        try:
            rds = aws.rds
            
            response = rds.describe_db_instances()
            
            for db in response.get("DBInstances", []):
                if not db.get("MultiAZ", False):
                    db_id = db["DBInstanceIdentifier"]
                    db_class = db["DBInstanceClass"]
                    az = db.get("AvailabilityZone", "")
                    
                    # Skip read replicas
                    if db.get("ReadReplicaSourceDBInstanceIdentifier"):
                        continue
                    
                    finding = SingleAZFinding(
                        finding_id=f"reliability-single-az-rds-{db_id}",
                        severity=Severity.HIGH,
                        title=f"Single-AZ RDS Instance: {db_id}",
                        description=f"RDS instance {db_id} ({db_class}) is deployed in a single AZ ({az}), creating a single point of failure.",
                        resource=ResourceBase(
                            resource_id=db_id,
                            resource_type=ResourceType.RDS_INSTANCE,
                            resource_name=db_id,
                            region=region,
                            account_id="",
                            tags={},
                        ),
                        recommendation="Enable Multi-AZ deployment for automatic failover and high availability.",
                        remediation_available=True,
                        availability_impact="high",
                        mttr_impact="Minutes to hours during AZ failure",
                        current_az=az,
                        recommended_azs=[f"{region}a", f"{region}b"],
                    )
                    self.findings.append(finding)
                    
        except Exception as e:
            logger.error("Error scanning single-AZ RDS", error=str(e), region=region)
    
    async def _scan_rds_no_backup(
        self, aws: AWSClientManager, region: str
    ) -> None:
        """Find RDS instances with no automated backups"""
        try:
            rds = aws.rds
            
            response = rds.describe_db_instances()
            
            for db in response.get("DBInstances", []):
                backup_retention = db.get("BackupRetentionPeriod", 0)
                
                if backup_retention == 0:
                    db_id = db["DBInstanceIdentifier"]
                    storage_gb = db.get("AllocatedStorage", 0)
                    create_time = db.get("InstanceCreateTime")
                    
                    age_days = 0
                    if create_time:
                        age_days = (datetime.utcnow().replace(tzinfo=create_time.tzinfo) - create_time).days
                    
                    finding = NoBackupFinding(
                        finding_id=f"reliability-no-backup-rds-{db_id}",
                        severity=Severity.CRITICAL,
                        title=f"RDS Without Backups: {db_id}",
                        description=f"RDS instance {db_id} has automated backups disabled. Data loss risk!",
                        resource=ResourceBase(
                            resource_id=db_id,
                            resource_type=ResourceType.RDS_INSTANCE,
                            resource_name=db_id,
                            region=region,
                            account_id="",
                            tags={},
                            created_at=create_time,
                        ),
                        recommendation="Enable automated backups with at least 7 days retention.",
                        remediation_available=True,
                        availability_impact="high",
                        resource_age_days=age_days,
                        data_size_gb=float(storage_gb),
                        recommended_backup_frequency="daily",
                    )
                    self.findings.append(finding)
                    
        except Exception as e:
            logger.error("Error scanning RDS backups", error=str(e), region=region)
    
    async def _scan_single_az_elb(
        self, aws: AWSClientManager, region: str
    ) -> None:
        """Find load balancers in single AZ"""
        try:
            elbv2 = aws.elbv2
            
            response = elbv2.describe_load_balancers()
            
            for lb in response.get("LoadBalancers", []):
                azs = lb.get("AvailabilityZones", [])
                
                if len(azs) == 1:
                    lb_name = lb["LoadBalancerName"]
                    lb_arn = lb["LoadBalancerArn"]
                    current_az = azs[0].get("ZoneName", "")
                    
                    finding = SingleAZFinding(
                        finding_id=f"reliability-single-az-elb-{lb_name}",
                        severity=Severity.HIGH,
                        title=f"Single-AZ Load Balancer: {lb_name}",
                        description=f"Load balancer {lb_name} is only deployed in one AZ ({current_az}).",
                        resource=ResourceBase(
                            resource_id=lb_arn,
                            resource_type=ResourceType.ELB,
                            resource_name=lb_name,
                            region=region,
                            account_id="",
                            tags={},
                        ),
                        recommendation="Add subnets from additional AZs for high availability.",
                        remediation_available=True,
                        availability_impact="high",
                        current_az=current_az,
                        recommended_azs=[f"{region}a", f"{region}b", f"{region}c"],
                    )
                    self.findings.append(finding)
                    
        except Exception as e:
            logger.error("Error scanning single-AZ ELB", error=str(e), region=region)
    
    async def _scan_ec2_no_autoscaling(
        self, aws: AWSClientManager, region: str
    ) -> None:
        """Find EC2 instances not in Auto Scaling groups"""
        try:
            ec2 = aws.ec2
            autoscaling = aws.get_client("autoscaling")
            
            # Get all Auto Scaling instances
            asg_response = autoscaling.describe_auto_scaling_instances()
            asg_instance_ids = {
                i["InstanceId"] for i in asg_response.get("AutoScalingInstances", [])
            }
            
            # Get all running instances
            ec2_response = ec2.describe_instances(
                Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
            )
            
            for reservation in ec2_response.get("Reservations", []):
                for instance in reservation.get("Instances", []):
                    instance_id = instance["InstanceId"]
                    
                    # Skip instances in ASG
                    if instance_id in asg_instance_ids:
                        continue
                    
                    # Skip instances with specific tags (might be intentionally standalone)
                    tags = {t["Key"]: t["Value"] for t in instance.get("Tags", [])}
                    if tags.get("aws:autoscaling:groupName"):
                        continue
                    
                    # Check if it looks like a production workload
                    instance_type = instance["InstanceType"]
                    name = tags.get("Name", "")
                    
                    # Skip tiny instances (likely dev/test)
                    if any(size in instance_type for size in ["nano", "micro"]):
                        continue
                    
                    finding = NoAutoScalingFinding(
                        finding_id=f"reliability-no-asg-{instance_id}",
                        severity=Severity.MEDIUM,
                        title=f"EC2 Without Auto Scaling: {instance_id}",
                        description=f"EC2 instance {instance_id} ({name or instance_type}) is not part of an Auto Scaling group.",
                        resource=ResourceBase(
                            resource_id=instance_id,
                            resource_type=ResourceType.EC2_INSTANCE,
                            resource_name=name,
                            region=region,
                            account_id=instance.get("OwnerId", ""),
                            tags=tags,
                            created_at=instance.get("LaunchTime"),
                        ),
                        recommendation="Consider using Auto Scaling for automatic replacement and scaling.",
                        remediation_available=False,
                        availability_impact="medium",
                        current_instance_count=1,
                        recommended_min=2,
                        recommended_max=4,
                    )
                    self.findings.append(finding)
                    
        except Exception as e:
            logger.error("Error scanning EC2 autoscaling", error=str(e), region=region)
    
    async def _scan_missing_cloudwatch_alarms(
        self, aws: AWSClientManager, region: str
    ) -> None:
        """Find EC2 instances without CloudWatch alarms"""
        try:
            ec2 = aws.ec2
            cw = aws.cloudwatch
            
            # Get all CloudWatch alarms for EC2
            alarms = cw.describe_alarms(AlarmTypes=["MetricAlarm"])
            
            # Get instance IDs with alarms
            instances_with_alarms = set()
            for alarm in alarms.get("MetricAlarms", []):
                for dim in alarm.get("Dimensions", []):
                    if dim["Name"] == "InstanceId":
                        instances_with_alarms.add(dim["Value"])
            
            # Get running instances
            response = ec2.describe_instances(
                Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
            )
            
            for reservation in response.get("Reservations", []):
                for instance in reservation.get("Instances", []):
                    instance_id = instance["InstanceId"]
                    instance_type = instance["InstanceType"]
                    
                    # Skip tiny instances
                    if any(size in instance_type for size in ["nano", "micro"]):
                        continue
                    
                    if instance_id not in instances_with_alarms:
                        tags = {t["Key"]: t["Value"] for t in instance.get("Tags", [])}
                        name = tags.get("Name", "")
                        
                        finding = HealthCheckFinding(
                            finding_id=f"reliability-no-alarm-{instance_id}",
                            severity=Severity.MEDIUM,
                            title=f"EC2 Without CloudWatch Alarms: {instance_id}",
                            description=f"EC2 instance {instance_id} ({name or instance_type}) has no CloudWatch alarms configured.",
                            resource=ResourceBase(
                                resource_id=instance_id,
                                resource_type=ResourceType.EC2_INSTANCE,
                                resource_name=name,
                                region=region,
                                account_id=instance.get("OwnerId", ""),
                                tags=tags,
                            ),
                            recommendation="Create CloudWatch alarms for CPU, memory, and disk metrics.",
                            remediation_available=True,
                            availability_impact="medium",
                            health_check_type="cloudwatch_alarm",
                            current_config=None,
                            recommended_config={
                                "cpu_alarm": {"threshold": 80, "period": 300},
                                "status_check_alarm": {"threshold": 1, "period": 60},
                            },
                        )
                        self.findings.append(finding)
                        
        except Exception as e:
            logger.error("Error scanning CloudWatch alarms", error=str(e), region=region)
    
    async def _scan_elb_health_checks(
        self, aws: AWSClientManager, region: str
    ) -> None:
        """Find load balancers with suboptimal health check config"""
        try:
            elbv2 = aws.elbv2
            
            # Get all target groups
            response = elbv2.describe_target_groups()
            
            for tg in response.get("TargetGroups", []):
                tg_arn = tg["TargetGroupArn"]
                tg_name = tg["TargetGroupName"]
                
                # Check health check configuration
                health_check_interval = tg.get("HealthCheckIntervalSeconds", 30)
                healthy_threshold = tg.get("HealthyThresholdCount", 5)
                unhealthy_threshold = tg.get("UnhealthyThresholdCount", 2)
                
                issues = []
                
                # Interval too long
                if health_check_interval > 30:
                    issues.append(f"Health check interval ({health_check_interval}s) is too long")
                
                # Healthy threshold too high (slow recovery)
                if healthy_threshold > 3:
                    issues.append(f"Healthy threshold ({healthy_threshold}) delays recovery")
                
                if issues:
                    finding = HealthCheckFinding(
                        finding_id=f"reliability-health-check-{tg_name}",
                        severity=Severity.LOW,
                        title=f"Suboptimal Health Check: {tg_name}",
                        description=f"Target group {tg_name} has suboptimal health check configuration: {'; '.join(issues)}",
                        resource=ResourceBase(
                            resource_id=tg_arn,
                            resource_type=ResourceType.ELB,
                            resource_name=tg_name,
                            region=region,
                            account_id="",
                            tags={},
                        ),
                        recommendation="Optimize health check settings for faster failure detection and recovery.",
                        remediation_available=True,
                        availability_impact="low",
                        health_check_type="elb_target_group",
                        current_config={
                            "interval": health_check_interval,
                            "healthy_threshold": healthy_threshold,
                            "unhealthy_threshold": unhealthy_threshold,
                        },
                        recommended_config={
                            "interval": 10,
                            "healthy_threshold": 2,
                            "unhealthy_threshold": 2,
                        },
                    )
                    self.findings.append(finding)
                    
        except Exception as e:
            logger.error("Error scanning ELB health checks", error=str(e), region=region)
    
    async def _scan_ebs_no_snapshots(
        self, aws: AWSClientManager, region: str
    ) -> None:
        """Find EBS volumes without recent snapshots"""
        try:
            ec2 = aws.ec2
            
            # Get all volumes
            volumes = ec2.describe_volumes().get("Volumes", [])
            
            # Get recent snapshots (last 30 days)
            cutoff = datetime.utcnow() - timedelta(days=30)
            snapshots = ec2.describe_snapshots(OwnerIds=["self"]).get("Snapshots", [])
            
            volumes_with_snapshots = set()
            for snap in snapshots:
                if snap["StartTime"].replace(tzinfo=None) > cutoff:
                    volumes_with_snapshots.add(snap.get("VolumeId", ""))
            
            for volume in volumes:
                volume_id = volume["VolumeId"]
                size_gb = volume["Size"]
                
                # Only check attached volumes (unattached are flagged by cost scanner)
                if volume["State"] != "in-use":
                    continue
                
                if volume_id not in volumes_with_snapshots:
                    create_time = volume.get("CreateTime")
                    age_days = 0
                    if create_time:
                        age_days = (datetime.utcnow().replace(tzinfo=create_time.tzinfo) - create_time).days
                    
                    finding = NoBackupFinding(
                        finding_id=f"reliability-no-snapshot-{volume_id}",
                        severity=Severity.MEDIUM,
                        title=f"EBS Without Recent Snapshot: {volume_id}",
                        description=f"EBS volume {volume_id} ({size_gb}GB) has no snapshots in the last 30 days.",
                        resource=ResourceBase(
                            resource_id=volume_id,
                            resource_type=ResourceType.EBS_VOLUME,
                            resource_name=self._get_name_tag(volume.get("Tags", [])),
                            region=region,
                            account_id="",
                            tags=self._tags_to_dict(volume.get("Tags", [])),
                            created_at=create_time,
                        ),
                        recommendation="Create regular snapshots using AWS Backup or Data Lifecycle Manager.",
                        remediation_available=True,
                        availability_impact="medium",
                        resource_age_days=age_days,
                        data_size_gb=float(size_gb),
                        recommended_backup_frequency="daily",
                    )
                    self.findings.append(finding)
                    
        except Exception as e:
            logger.error("Error scanning EBS snapshots", error=str(e), region=region)
    
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
