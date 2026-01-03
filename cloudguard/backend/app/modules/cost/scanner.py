"""
Cost Scanner - Scans AWS resources for cost optimization opportunities
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
    IdleResourceFinding,
    OversizedResourceFinding,
    UnattachedResourceFinding,
    ReservedInstanceOpportunity,
    CostFinding,
)

logger = structlog.get_logger()


class CostScanner:
    """
    Scans AWS resources for cost optimization opportunities:
    - Idle resources (low utilization)
    - Oversized instances (rightsizing)
    - Unattached resources (orphaned EBS, EIPs)
    - On-demand vs Reserved/Savings Plans opportunities
    """
    
    def __init__(self, aws_client: AWSClientManager):
        self.aws = aws_client
        self.settings = get_settings()
        self.findings: list[CostFinding] = []
    
    async def scan_all(self, regions: Optional[list[str]] = None) -> list[CostFinding]:
        """Run all cost optimization scans"""
        regions = regions or [self.settings.aws_region]
        self.findings = []
        
        for region in regions:
            logger.info("Scanning region for cost optimization", region=region)
            
            # Create region-specific client
            regional_aws = AWSClientManager(region=region)
            
            # Run all scanners
            await self._scan_idle_ec2_instances(regional_aws, region)
            await self._scan_oversized_instances(regional_aws, region)
            await self._scan_unattached_ebs_volumes(regional_aws, region)
            await self._scan_unattached_eips(regional_aws, region)
            await self._scan_old_snapshots(regional_aws, region)
            await self._scan_idle_rds_instances(regional_aws, region)
            await self._scan_idle_load_balancers(regional_aws, region)
        
        # Global scans (not region-specific)
        await self._scan_reserved_instance_opportunities()
        await self._scan_unused_elastic_ips()
        
        logger.info("Cost scan completed", findings_count=len(self.findings))
        return self.findings
    
    async def _scan_idle_ec2_instances(
        self, aws: AWSClientManager, region: str
    ) -> None:
        """Find EC2 instances with consistently low CPU utilization"""
        try:
            ec2 = aws.ec2
            cw = aws.cloudwatch
            
            # Get all running instances
            response = ec2.describe_instances(
                Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
            )
            
            for reservation in response.get("Reservations", []):
                for instance in reservation.get("Instances", []):
                    instance_id = instance["InstanceId"]
                    instance_type = instance["InstanceType"]
                    
                    # Get CPU utilization for the past 7 days
                    end_time = datetime.utcnow()
                    start_time = end_time - timedelta(days=self.settings.idle_resource_days)
                    
                    metrics = cw.get_metric_statistics(
                        Namespace="AWS/EC2",
                        MetricName="CPUUtilization",
                        Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                        StartTime=start_time,
                        EndTime=end_time,
                        Period=3600,  # 1 hour
                        Statistics=["Average", "Maximum"],
                    )
                    
                    if metrics.get("Datapoints"):
                        avg_cpu = sum(d["Average"] for d in metrics["Datapoints"]) / len(
                            metrics["Datapoints"]
                        )
                        max_cpu = max(d["Maximum"] for d in metrics["Datapoints"])
                        
                        # Check if instance is idle (< 10% average CPU)
                        if avg_cpu < self.settings.low_utilization_threshold:
                            # Estimate monthly cost (simplified)
                            monthly_cost = self._estimate_ec2_monthly_cost(instance_type)
                            
                            finding = IdleResourceFinding(
                                finding_id=f"cost-idle-ec2-{instance_id}",
                                severity=Severity.MEDIUM if monthly_cost < 100 else Severity.HIGH,
                                title=f"Idle EC2 Instance: {instance_id}",
                                description=f"Instance {instance_id} ({instance_type}) has average CPU utilization of {avg_cpu:.1f}% over the past {self.settings.idle_resource_days} days.",
                                resource=ResourceBase(
                                    resource_id=instance_id,
                                    resource_type=ResourceType.EC2_INSTANCE,
                                    resource_name=self._get_name_tag(instance.get("Tags", [])),
                                    region=region,
                                    account_id=self._get_account_id(instance),
                                    tags=self._tags_to_dict(instance.get("Tags", [])),
                                    created_at=instance.get("LaunchTime"),
                                ),
                                recommendation=f"Consider stopping or terminating this instance, or rightsize to a smaller instance type. Current utilization: {avg_cpu:.1f}%",
                                estimated_savings=monthly_cost * 0.9,  # Assuming 90% savings if terminated
                                remediation_available=True,
                                current_monthly_cost=monthly_cost,
                                optimized_monthly_cost=monthly_cost * 0.1,
                                savings_percentage=90.0,
                                idle_days=self.settings.idle_resource_days,
                                utilization_metrics={"avg_cpu": avg_cpu, "max_cpu": max_cpu},
                            )
                            self.findings.append(finding)
                            logger.debug("Found idle EC2 instance", instance_id=instance_id, avg_cpu=avg_cpu)
                            
        except Exception as e:
            logger.error("Error scanning idle EC2 instances", error=str(e), region=region)
    
    async def _scan_oversized_instances(
        self, aws: AWSClientManager, region: str
    ) -> None:
        """Find EC2 instances that could be downsized"""
        try:
            ec2 = aws.ec2
            cw = aws.cloudwatch
            
            response = ec2.describe_instances(
                Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
            )
            
            for reservation in response.get("Reservations", []):
                for instance in reservation.get("Instances", []):
                    instance_id = instance["InstanceId"]
                    instance_type = instance["InstanceType"]
                    
                    # Skip nano/micro instances (already small)
                    if any(size in instance_type for size in ["nano", "micro"]):
                        continue
                    
                    # Get CPU metrics
                    end_time = datetime.utcnow()
                    start_time = end_time - timedelta(days=14)  # 2 weeks of data
                    
                    metrics = cw.get_metric_statistics(
                        Namespace="AWS/EC2",
                        MetricName="CPUUtilization",
                        Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                        StartTime=start_time,
                        EndTime=end_time,
                        Period=3600,
                        Statistics=["Average", "Maximum"],
                    )
                    
                    if metrics.get("Datapoints"):
                        avg_cpu = sum(d["Average"] for d in metrics["Datapoints"]) / len(
                            metrics["Datapoints"]
                        )
                        peak_cpu = max(d["Maximum"] for d in metrics["Datapoints"])
                        
                        # If peak CPU never exceeds 40%, suggest downsizing
                        if peak_cpu < 40 and avg_cpu < 20:
                            current_cost = self._estimate_ec2_monthly_cost(instance_type)
                            recommended_type = self._get_smaller_instance_type(instance_type)
                            recommended_cost = self._estimate_ec2_monthly_cost(recommended_type)
                            
                            finding = OversizedResourceFinding(
                                finding_id=f"cost-oversized-ec2-{instance_id}",
                                severity=Severity.MEDIUM,
                                title=f"Oversized EC2 Instance: {instance_id}",
                                description=f"Instance {instance_id} is oversized. Peak CPU: {peak_cpu:.1f}%, Avg CPU: {avg_cpu:.1f}%",
                                resource=ResourceBase(
                                    resource_id=instance_id,
                                    resource_type=ResourceType.EC2_INSTANCE,
                                    resource_name=self._get_name_tag(instance.get("Tags", [])),
                                    region=region,
                                    account_id=self._get_account_id(instance),
                                    tags=self._tags_to_dict(instance.get("Tags", [])),
                                ),
                                recommendation=f"Rightsize from {instance_type} to {recommended_type}",
                                estimated_savings=current_cost - recommended_cost,
                                remediation_available=True,
                                current_monthly_cost=current_cost,
                                optimized_monthly_cost=recommended_cost,
                                savings_percentage=((current_cost - recommended_cost) / current_cost) * 100,
                                current_size=instance_type,
                                recommended_size=recommended_type,
                                avg_cpu_utilization=avg_cpu,
                                peak_cpu_utilization=peak_cpu,
                            )
                            self.findings.append(finding)
                            
        except Exception as e:
            logger.error("Error scanning oversized instances", error=str(e), region=region)
    
    async def _scan_unattached_ebs_volumes(
        self, aws: AWSClientManager, region: str
    ) -> None:
        """Find EBS volumes not attached to any instance"""
        try:
            ec2 = aws.ec2
            
            response = ec2.describe_volumes(
                Filters=[{"Name": "status", "Values": ["available"]}]
            )
            
            for volume in response.get("Volumes", []):
                volume_id = volume["VolumeId"]
                size_gb = volume["Size"]
                volume_type = volume["VolumeType"]
                create_time = volume["CreateTime"]
                
                # Calculate days unattached
                days_unattached = (datetime.utcnow().replace(tzinfo=create_time.tzinfo) - create_time).days
                
                # Calculate monthly cost
                monthly_cost = self._estimate_ebs_monthly_cost(size_gb, volume_type)
                
                finding = UnattachedResourceFinding(
                    finding_id=f"cost-unattached-ebs-{volume_id}",
                    severity=Severity.HIGH if monthly_cost > 50 else Severity.MEDIUM,
                    title=f"Unattached EBS Volume: {volume_id}",
                    description=f"EBS volume {volume_id} ({size_gb}GB, {volume_type}) has been unattached for {days_unattached} days.",
                    resource=ResourceBase(
                        resource_id=volume_id,
                        resource_type=ResourceType.EBS_VOLUME,
                        resource_name=self._get_name_tag(volume.get("Tags", [])),
                        region=region,
                        account_id="",  # EBS doesn't include account in response
                        tags=self._tags_to_dict(volume.get("Tags", [])),
                        created_at=create_time,
                    ),
                    recommendation="Delete this volume if data is no longer needed, or create a snapshot and delete.",
                    estimated_savings=monthly_cost,
                    remediation_available=True,
                    current_monthly_cost=monthly_cost,
                    optimized_monthly_cost=0,
                    savings_percentage=100.0,
                    unattached_days=days_unattached,
                )
                self.findings.append(finding)
                
        except Exception as e:
            logger.error("Error scanning unattached EBS volumes", error=str(e), region=region)
    
    async def _scan_unattached_eips(
        self, aws: AWSClientManager, region: str
    ) -> None:
        """Find Elastic IPs not associated with any resource"""
        try:
            ec2 = aws.ec2
            
            response = ec2.describe_addresses()
            
            for address in response.get("Addresses", []):
                if "AssociationId" not in address:
                    allocation_id = address.get("AllocationId", address.get("PublicIp"))
                    public_ip = address["PublicIp"]
                    
                    # Unattached EIPs cost ~$3.60/month
                    monthly_cost = 3.60
                    
                    finding = UnattachedResourceFinding(
                        finding_id=f"cost-unattached-eip-{allocation_id}",
                        severity=Severity.LOW,
                        title=f"Unattached Elastic IP: {public_ip}",
                        description=f"Elastic IP {public_ip} is not associated with any instance or NAT gateway.",
                        resource=ResourceBase(
                            resource_id=allocation_id,
                            resource_type=ResourceType.EC2_EIP,
                            resource_name=public_ip,
                            region=region,
                            account_id="",
                            tags=self._tags_to_dict(address.get("Tags", [])),
                        ),
                        recommendation="Release this Elastic IP if it's no longer needed.",
                        estimated_savings=monthly_cost,
                        remediation_available=True,
                        current_monthly_cost=monthly_cost,
                        optimized_monthly_cost=0,
                        savings_percentage=100.0,
                        unattached_days=0,  # We don't know when it was detached
                    )
                    self.findings.append(finding)
                    
        except Exception as e:
            logger.error("Error scanning unattached EIPs", error=str(e), region=region)
    
    async def _scan_old_snapshots(
        self, aws: AWSClientManager, region: str
    ) -> None:
        """Find old EBS snapshots that could be deleted"""
        try:
            ec2 = aws.ec2
            
            # Get snapshots owned by this account
            response = ec2.describe_snapshots(OwnerIds=["self"])
            
            cutoff_date = datetime.utcnow() - timedelta(days=90)  # 90 days old
            
            for snapshot in response.get("Snapshots", []):
                start_time = snapshot["StartTime"]
                
                if start_time.replace(tzinfo=None) < cutoff_date:
                    snapshot_id = snapshot["SnapshotId"]
                    size_gb = snapshot["VolumeSize"]
                    age_days = (datetime.utcnow().replace(tzinfo=start_time.tzinfo) - start_time).days
                    
                    # Snapshot storage: ~$0.05/GB/month
                    monthly_cost = size_gb * 0.05
                    
                    finding = UnattachedResourceFinding(
                        finding_id=f"cost-old-snapshot-{snapshot_id}",
                        severity=Severity.LOW,
                        title=f"Old EBS Snapshot: {snapshot_id}",
                        description=f"Snapshot {snapshot_id} is {age_days} days old and consuming {size_gb}GB.",
                        resource=ResourceBase(
                            resource_id=snapshot_id,
                            resource_type=ResourceType.EC2_SNAPSHOT,
                            resource_name=snapshot.get("Description", ""),
                            region=region,
                            account_id=snapshot.get("OwnerId", ""),
                            tags=self._tags_to_dict(snapshot.get("Tags", [])),
                            created_at=start_time,
                        ),
                        recommendation="Review and delete this snapshot if the data is no longer needed.",
                        estimated_savings=monthly_cost,
                        remediation_available=True,
                        current_monthly_cost=monthly_cost,
                        optimized_monthly_cost=0,
                        savings_percentage=100.0,
                        unattached_days=age_days,
                    )
                    self.findings.append(finding)
                    
        except Exception as e:
            logger.error("Error scanning old snapshots", error=str(e), region=region)
    
    async def _scan_idle_rds_instances(
        self, aws: AWSClientManager, region: str
    ) -> None:
        """Find RDS instances with low connection counts"""
        try:
            rds = aws.rds
            cw = aws.cloudwatch
            
            response = rds.describe_db_instances()
            
            for db in response.get("DBInstances", []):
                db_id = db["DBInstanceIdentifier"]
                instance_class = db["DBInstanceClass"]
                
                if db["DBInstanceStatus"] != "available":
                    continue
                
                # Check connection count
                end_time = datetime.utcnow()
                start_time = end_time - timedelta(days=7)
                
                metrics = cw.get_metric_statistics(
                    Namespace="AWS/RDS",
                    MetricName="DatabaseConnections",
                    Dimensions=[{"Name": "DBInstanceIdentifier", "Value": db_id}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=3600,
                    Statistics=["Average", "Maximum"],
                )
                
                if metrics.get("Datapoints"):
                    max_connections = max(d["Maximum"] for d in metrics["Datapoints"])
                    avg_connections = sum(d["Average"] for d in metrics["Datapoints"]) / len(
                        metrics["Datapoints"]
                    )
                    
                    # If max connections < 5 over a week, likely idle
                    if max_connections < 5:
                        monthly_cost = self._estimate_rds_monthly_cost(instance_class)
                        
                        finding = IdleResourceFinding(
                            finding_id=f"cost-idle-rds-{db_id}",
                            severity=Severity.HIGH,  # RDS is expensive
                            title=f"Idle RDS Instance: {db_id}",
                            description=f"RDS instance {db_id} ({instance_class}) has max {max_connections} connections over the past week.",
                            resource=ResourceBase(
                                resource_id=db_id,
                                resource_type=ResourceType.RDS_INSTANCE,
                                resource_name=db_id,
                                region=region,
                                account_id="",
                                tags=[],
                            ),
                            recommendation="Consider stopping or deleting this RDS instance if not in use.",
                            estimated_savings=monthly_cost,
                            remediation_available=True,
                            current_monthly_cost=monthly_cost,
                            optimized_monthly_cost=0,
                            savings_percentage=100.0,
                            idle_days=7,
                            utilization_metrics={
                                "max_connections": max_connections,
                                "avg_connections": avg_connections,
                            },
                        )
                        self.findings.append(finding)
                        
        except Exception as e:
            logger.error("Error scanning idle RDS instances", error=str(e), region=region)
    
    async def _scan_idle_load_balancers(
        self, aws: AWSClientManager, region: str
    ) -> None:
        """Find load balancers with no healthy targets or low request count"""
        try:
            elbv2 = aws.elbv2
            cw = aws.cloudwatch
            
            response = elbv2.describe_load_balancers()
            
            for lb in response.get("LoadBalancers", []):
                lb_arn = lb["LoadBalancerArn"]
                lb_name = lb["LoadBalancerName"]
                lb_type = lb["Type"]
                
                # Check request count
                end_time = datetime.utcnow()
                start_time = end_time - timedelta(days=7)
                
                metric_name = "RequestCount" if lb_type == "application" else "ProcessedBytes"
                
                metrics = cw.get_metric_statistics(
                    Namespace="AWS/ApplicationELB" if lb_type == "application" else "AWS/NetworkELB",
                    MetricName=metric_name,
                    Dimensions=[{"Name": "LoadBalancer", "Value": lb_arn.split("/", 1)[1]}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=86400,  # Daily
                    Statistics=["Sum"],
                )
                
                total_requests = sum(d["Sum"] for d in metrics.get("Datapoints", []))
                
                # If fewer than 100 requests in a week, likely idle
                if total_requests < 100:
                    monthly_cost = 22.0 if lb_type == "application" else 18.0  # Rough estimates
                    
                    finding = IdleResourceFinding(
                        finding_id=f"cost-idle-elb-{lb_name}",
                        severity=Severity.MEDIUM,
                        title=f"Idle Load Balancer: {lb_name}",
                        description=f"Load balancer {lb_name} has only {int(total_requests)} requests in the past week.",
                        resource=ResourceBase(
                            resource_id=lb_arn,
                            resource_type=ResourceType.ELB,
                            resource_name=lb_name,
                            region=region,
                            account_id="",
                            tags=[],
                        ),
                        recommendation="Delete this load balancer if it's no longer needed.",
                        estimated_savings=monthly_cost,
                        remediation_available=True,
                        current_monthly_cost=monthly_cost,
                        optimized_monthly_cost=0,
                        savings_percentage=100.0,
                        idle_days=7,
                        utilization_metrics={"total_requests_7d": total_requests},
                    )
                    self.findings.append(finding)
                    
        except Exception as e:
            logger.error("Error scanning idle load balancers", error=str(e), region=region)
    
    async def _scan_reserved_instance_opportunities(self) -> None:
        """Analyze on-demand usage for Reserved Instance opportunities"""
        try:
            ce = self.aws.ce
            
            end_date = datetime.utcnow().strftime("%Y-%m-%d")
            start_date = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
            
            # Get RI recommendations from Cost Explorer
            response = ce.get_reservation_purchase_recommendation(
                Service="Amazon Elastic Compute Cloud - Compute",
                LookbackPeriodInDays="THIRTY_DAYS",
                TermInYears="ONE_YEAR",
                PaymentOption="NO_UPFRONT",
            )
            
            for rec in response.get("Recommendations", []):
                for detail in rec.get("RecommendationDetails", []):
                    instance_type = detail.get("InstanceDetails", {}).get("EC2InstanceDetails", {}).get("InstanceType", "Unknown")
                    monthly_savings = float(detail.get("EstimatedMonthlySavingsAmount", 0))
                    
                    if monthly_savings > 10:  # Only report significant savings
                        finding = ReservedInstanceOpportunity(
                            finding_id=f"cost-ri-opportunity-{instance_type}",
                            severity=Severity.MEDIUM if monthly_savings < 100 else Severity.HIGH,
                            title=f"Reserved Instance Opportunity: {instance_type}",
                            description=f"Purchasing Reserved Instances for {instance_type} could save ${monthly_savings:.2f}/month.",
                            resource=ResourceBase(
                                resource_id=f"ri-{instance_type}",
                                resource_type=ResourceType.EC2_INSTANCE,
                                resource_name=instance_type,
                                region=self.settings.aws_region,
                                account_id="",
                                tags={},
                            ),
                            recommendation=f"Consider purchasing a 1-year Reserved Instance for {instance_type}.",
                            estimated_savings=monthly_savings,
                            remediation_available=False,  # RI purchase needs manual approval
                            current_monthly_cost=float(detail.get("EstimatedMonthlyOnDemandCost", 0)),
                            optimized_monthly_cost=float(detail.get("EstimatedReservationCostForLookbackPeriod", 0)) / 12,
                            savings_percentage=float(detail.get("EstimatedMonthlySavingsPercentage", 0)),
                            on_demand_hours=float(detail.get("CurrentMaximumHourlyOnDemandSpend", 0)) * 720,
                            recommended_commitment="1yr-no-upfront",
                            break_even_months=7,  # Typical break-even for 1yr no-upfront
                        )
                        self.findings.append(finding)
                        
        except Exception as e:
            logger.error("Error analyzing RI opportunities", error=str(e))
    
    async def _scan_unused_elastic_ips(self) -> None:
        """Scan for unused EIPs across all regions"""
        # Already covered in regional scan
        pass
    
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
    
    def _get_account_id(self, instance: dict) -> str:
        """Extract account ID from instance ARN or owner"""
        return instance.get("OwnerId", "")
    
    def _estimate_ec2_monthly_cost(self, instance_type: str) -> float:
        """Estimate monthly cost for EC2 instance type (simplified)"""
        # Real implementation would use AWS Pricing API
        pricing = {
            "t3.nano": 3.80, "t3.micro": 7.60, "t3.small": 15.20, "t3.medium": 30.40,
            "t3.large": 60.80, "t3.xlarge": 121.60, "t3.2xlarge": 243.20,
            "t2.nano": 4.18, "t2.micro": 8.35, "t2.small": 16.70, "t2.medium": 33.41,
            "m5.large": 70.08, "m5.xlarge": 140.16, "m5.2xlarge": 280.32,
            "m5.4xlarge": 560.64, "m5.8xlarge": 1121.28,
            "c5.large": 62.05, "c5.xlarge": 124.10, "c5.2xlarge": 248.20,
            "r5.large": 91.98, "r5.xlarge": 183.96, "r5.2xlarge": 367.92,
        }
        return pricing.get(instance_type, 100.0)  # Default to $100/month
    
    def _estimate_ebs_monthly_cost(self, size_gb: int, volume_type: str) -> float:
        """Estimate monthly cost for EBS volume"""
        pricing_per_gb = {
            "gp3": 0.08, "gp2": 0.10, "io1": 0.125, "io2": 0.125,
            "st1": 0.045, "sc1": 0.025, "standard": 0.05,
        }
        return size_gb * pricing_per_gb.get(volume_type, 0.10)
    
    def _estimate_rds_monthly_cost(self, instance_class: str) -> float:
        """Estimate monthly cost for RDS instance"""
        pricing = {
            "db.t3.micro": 12.41, "db.t3.small": 24.82, "db.t3.medium": 49.64,
            "db.t3.large": 99.28, "db.m5.large": 124.10, "db.m5.xlarge": 248.20,
            "db.r5.large": 175.20, "db.r5.xlarge": 350.40,
        }
        return pricing.get(instance_class, 200.0)
    
    def _get_smaller_instance_type(self, instance_type: str) -> str:
        """Get the next smaller instance type"""
        size_order = ["nano", "micro", "small", "medium", "large", "xlarge", "2xlarge", "4xlarge", "8xlarge"]
        
        parts = instance_type.rsplit(".", 1)
        if len(parts) != 2:
            return instance_type
        
        family, size = parts
        
        try:
            current_idx = size_order.index(size)
            if current_idx > 0:
                return f"{family}.{size_order[current_idx - 1]}"
        except ValueError:
            pass
        
        return instance_type
