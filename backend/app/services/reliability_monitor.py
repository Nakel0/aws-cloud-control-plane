"""
Reliability Monitoring Service
Monitors AWS infrastructure health and predicts issues
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from app.services.aws_client import AWSClient

logger = logging.getLogger(__name__)


class ReliabilityMonitor:
    """
    AWS Reliability Monitor
    
    Monitors:
    - Resource health (EC2, RDS, ELB)
    - Service limits
    - Multi-AZ configuration
    - Backup strategies
    - Certificate expirations
    """
    
    def __init__(self, aws_client: AWSClient):
        self.aws_client = aws_client
        self.issues = []
    
    def run_full_check(self) -> List[Dict[str, Any]]:
        """
        Run all reliability checks
        
        Returns:
            List of reliability issues found
        """
        self.issues = []
        
        logger.info("Starting full reliability check...")
        
        # Resource health checks
        self.check_ec2_health()
        self.check_rds_health()
        self.check_elb_health()
        
        # Architecture checks
        self.check_multi_az_configuration()
        self.check_backup_strategies()
        
        # Service limits
        self.check_service_limits()
        
        # Expiration checks
        self.check_certificate_expirations()
        
        logger.info(f"Reliability check completed. Found {len(self.issues)} issues.")
        return self.issues
    
    # ==================== Resource Health Checks ====================
    
    def check_ec2_health(self):
        """Check EC2 instance health"""
        try:
            ec2 = self.aws_client.get_client('ec2')
            
            # Get all running instances
            response = ec2.describe_instances(
                Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
            )
            
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    instance_id = instance['InstanceId']
                    
                    # Check system status
                    status = ec2.describe_instance_status(InstanceIds=[instance_id])
                    
                    if status['InstanceStatuses']:
                        instance_status = status['InstanceStatuses'][0]
                        
                        # Check system status
                        system_status = instance_status['SystemStatus']['Status']
                        if system_status != 'ok':
                            self.issues.append({
                                'type': 'reliability',
                                'category': 'ec2_health',
                                'severity': 'high',
                                'resource_id': instance_id,
                                'resource_type': 'ec2_instance',
                                'title': f'EC2 instance system status check failed: {instance_id}',
                                'description': f'System status is {system_status}',
                                'recommendation': 'Investigate system-level issues. May require instance stop/start.',
                                'evidence': {
                                    'instance_id': instance_id,
                                    'system_status': system_status
                                }
                            })
                        
                        # Check instance status
                        instance_status_check = instance_status['InstanceStatus']['Status']
                        if instance_status_check != 'ok':
                            self.issues.append({
                                'type': 'reliability',
                                'category': 'ec2_health',
                                'severity': 'high',
                                'resource_id': instance_id,
                                'resource_type': 'ec2_instance',
                                'title': f'EC2 instance status check failed: {instance_id}',
                                'description': f'Instance status is {instance_status_check}',
                                'recommendation': 'Check instance logs and application health.',
                                'evidence': {
                                    'instance_id': instance_id,
                                    'instance_status': instance_status_check
                                }
                            })
        
        except Exception as e:
            logger.error(f"Failed to check EC2 health: {e}")
    
    def check_rds_health(self):
        """Check RDS instance health"""
        try:
            rds = self.aws_client.get_client('rds')
            
            # Get all RDS instances
            response = rds.describe_db_instances()
            
            for db in response['DBInstances']:
                db_id = db['DBInstanceIdentifier']
                
                # Check storage space
                allocated_storage = db['AllocatedStorage']  # In GB
                
                # Get storage metrics from CloudWatch
                cloudwatch = self.aws_client.get_client('cloudwatch')
                
                # Get free storage space
                storage_metrics = cloudwatch.get_metric_statistics(
                    Namespace='AWS/RDS',
                    MetricName='FreeStorageSpace',
                    Dimensions=[{'Name': 'DBInstanceIdentifier', 'Value': db_id}],
                    StartTime=datetime.utcnow() - timedelta(hours=1),
                    EndTime=datetime.utcnow(),
                    Period=3600,
                    Statistics=['Average']
                )
                
                if storage_metrics['Datapoints']:
                    free_storage_bytes = storage_metrics['Datapoints'][0]['Average']
                    free_storage_gb = free_storage_bytes / (1024**3)
                    used_percent = ((allocated_storage - free_storage_gb) / allocated_storage) * 100
                    
                    # Alert if >80% full
                    if used_percent > 80:
                        days_until_full = self._estimate_days_until_full(
                            free_storage_gb,
                            allocated_storage
                        )
                        
                        self.issues.append({
                            'type': 'reliability',
                            'category': 'rds_storage',
                            'severity': 'high' if used_percent > 90 else 'medium',
                            'resource_id': db['DBInstanceArn'],
                            'resource_type': 'rds_instance',
                            'title': f'RDS storage running low: {db_id}',
                            'description': f'Storage is {used_percent:.1f}% full',
                            'recommendation': f'Increase storage allocation. Estimated {days_until_full} days until full.',
                            'evidence': {
                                'db_instance': db_id,
                                'allocated_storage_gb': allocated_storage,
                                'free_storage_gb': round(free_storage_gb, 2),
                                'used_percent': round(used_percent, 1),
                                'days_until_full': days_until_full
                            }
                        })
                
                # Check for read replica lag
                if 'ReadReplicaDBInstanceIdentifiers' in db and db['ReadReplicaDBInstanceIdentifiers']:
                    for replica_id in db['ReadReplicaDBInstanceIdentifiers']:
                        # Get replica lag
                        lag_metrics = cloudwatch.get_metric_statistics(
                            Namespace='AWS/RDS',
                            MetricName='ReplicaLag',
                            Dimensions=[{'Name': 'DBInstanceIdentifier', 'Value': replica_id}],
                            StartTime=datetime.utcnow() - timedelta(hours=1),
                            EndTime=datetime.utcnow(),
                            Period=3600,
                            Statistics=['Average']
                        )
                        
                        if lag_metrics['Datapoints']:
                            lag_seconds = lag_metrics['Datapoints'][0]['Average']
                            
                            # Alert if lag > 60 seconds
                            if lag_seconds > 60:
                                self.issues.append({
                                    'type': 'reliability',
                                    'category': 'rds_replication',
                                    'severity': 'medium',
                                    'resource_id': replica_id,
                                    'resource_type': 'rds_replica',
                                    'title': f'RDS replica lag detected: {replica_id}',
                                    'description': f'Replica is lagging {lag_seconds:.0f} seconds behind master',
                                    'recommendation': 'Investigate replication performance. Consider upgrading instance class.',
                                    'evidence': {
                                        'replica_id': replica_id,
                                        'master_id': db_id,
                                        'lag_seconds': round(lag_seconds, 0)
                                    }
                                })
        
        except Exception as e:
            logger.error(f"Failed to check RDS health: {e}")
    
    def check_elb_health(self):
        """Check Load Balancer health"""
        try:
            elbv2 = self.aws_client.get_client('elbv2')
            
            # Get all load balancers
            lbs = elbv2.describe_load_balancers()
            
            for lb in lbs['LoadBalancers']:
                lb_arn = lb['LoadBalancerArn']
                lb_name = lb['LoadBalancerName']
                
                # Get target groups
                target_groups = elbv2.describe_target_groups(LoadBalancerArn=lb_arn)
                
                for tg in target_groups['TargetGroups']:
                    tg_arn = tg['TargetGroupArn']
                    
                    # Check target health
                    health = elbv2.describe_target_health(TargetGroupArn=tg_arn)
                    
                    unhealthy_targets = []
                    for target in health['TargetHealthDescriptions']:
                        if target['TargetHealth']['State'] != 'healthy':
                            unhealthy_targets.append({
                                'target_id': target['Target']['Id'],
                                'state': target['TargetHealth']['State'],
                                'reason': target['TargetHealth'].get('Reason', 'Unknown')
                            })
                    
                    if unhealthy_targets:
                        self.issues.append({
                            'type': 'reliability',
                            'category': 'elb_health',
                            'severity': 'high',
                            'resource_id': lb_arn,
                            'resource_type': 'load_balancer',
                            'title': f'Unhealthy targets in load balancer: {lb_name}',
                            'description': f'{len(unhealthy_targets)} unhealthy targets detected',
                            'recommendation': 'Investigate unhealthy targets. Check application health and connectivity.',
                            'evidence': {
                                'load_balancer': lb_name,
                                'target_group': tg['TargetGroupName'],
                                'unhealthy_targets': unhealthy_targets
                            }
                        })
        
        except Exception as e:
            logger.error(f"Failed to check ELB health: {e}")
    
    # ==================== Architecture Checks ====================
    
    def check_multi_az_configuration(self):
        """Check if critical resources are in multiple AZs"""
        try:
            rds = self.aws_client.get_client('rds')
            
            # Check RDS instances
            response = rds.describe_db_instances()
            
            for db in response['DBInstances']:
                if not db.get('MultiAZ', False):
                    # Check if this is production (based on tags or instance size)
                    instance_class = db['DBInstanceClass']
                    
                    # Assume production if instance class is medium or larger
                    if any(size in instance_class for size in ['large', 'xlarge', '2xlarge']):
                        self.issues.append({
                            'type': 'reliability',
                            'category': 'multi_az',
                            'severity': 'medium',
                            'resource_id': db['DBInstanceArn'],
                            'resource_type': 'rds_instance',
                            'title': f'RDS instance not configured for Multi-AZ: {db["DBInstanceIdentifier"]}',
                            'description': 'Single AZ deployment creates single point of failure',
                            'recommendation': 'Enable Multi-AZ for high availability.',
                            'evidence': {
                                'db_instance': db['DBInstanceIdentifier'],
                                'multi_az': False,
                                'instance_class': instance_class
                            }
                        })
        
        except Exception as e:
            logger.error(f"Failed to check Multi-AZ configuration: {e}")
    
    def check_backup_strategies(self):
        """Check if backups are configured"""
        try:
            rds = self.aws_client.get_client('rds')
            
            # Check RDS backups
            response = rds.describe_db_instances()
            
            for db in response['DBInstances']:
                backup_retention = db.get('BackupRetentionPeriod', 0)
                
                if backup_retention == 0:
                    self.issues.append({
                        'type': 'reliability',
                        'category': 'backups',
                        'severity': 'high',
                        'resource_id': db['DBInstanceArn'],
                        'resource_type': 'rds_instance',
                        'title': f'RDS backups not enabled: {db["DBInstanceIdentifier"]}',
                        'description': 'No automated backups configured',
                        'recommendation': 'Enable automated backups with appropriate retention period (7-35 days).',
                        'evidence': {
                            'db_instance': db['DBInstanceIdentifier'],
                            'backup_retention_days': backup_retention
                        }
                    })
                elif backup_retention < 7:
                    self.issues.append({
                        'type': 'reliability',
                        'category': 'backups',
                        'severity': 'low',
                        'resource_id': db['DBInstanceArn'],
                        'resource_type': 'rds_instance',
                        'title': f'RDS backup retention too short: {db["DBInstanceIdentifier"]}',
                        'description': f'Backup retention is only {backup_retention} days',
                        'recommendation': 'Consider increasing retention to 7+ days for production databases.',
                        'evidence': {
                            'db_instance': db['DBInstanceIdentifier'],
                            'backup_retention_days': backup_retention,
                            'recommended_minimum': 7
                        }
                    })
        
        except Exception as e:
            logger.error(f"Failed to check backup strategies: {e}")
    
    # ==================== Service Limits ====================
    
    def check_service_limits(self):
        """Check AWS service limits"""
        try:
            # This is a simplified version. In production, use Service Quotas API
            ec2 = self.aws_client.get_client('ec2')
            
            # Get VPC information
            vpcs = ec2.describe_vpcs()
            
            for vpc in vpcs['Vpcs']:
                vpc_id = vpc['VpcId']
                
                # Check subnet count (limit is typically 200)
                subnets = ec2.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
                subnet_count = len(subnets['Subnets'])
                
                if subnet_count > 180:  # 90% of limit
                    self.issues.append({
                        'type': 'reliability',
                        'category': 'service_limits',
                        'severity': 'medium',
                        'resource_id': vpc_id,
                        'resource_type': 'vpc',
                        'title': f'VPC approaching subnet limit: {vpc_id}',
                        'description': f'{subnet_count} subnets out of 200 limit (90%+)',
                        'recommendation': 'Plan for subnet consolidation or request limit increase.',
                        'evidence': {
                            'vpc_id': vpc_id,
                            'current_subnets': subnet_count,
                            'limit': 200,
                            'utilization_percent': round((subnet_count / 200) * 100, 1)
                        }
                    })
        
        except Exception as e:
            logger.error(f"Failed to check service limits: {e}")
    
    # ==================== Expiration Checks ====================
    
    def check_certificate_expirations(self):
        """Check SSL/TLS certificate expirations"""
        try:
            acm = self.aws_client.get_client('acm')
            
            # List all certificates
            certs = acm.list_certificates(CertificateStatuses=['ISSUED'])
            
            now = datetime.now(datetime.utcnow().astimezone().tzinfo)
            
            for cert_summary in certs['CertificateSummaryList']:
                cert_arn = cert_summary['CertificateArn']
                
                # Get certificate details
                cert = acm.describe_certificate(CertificateArn=cert_arn)
                cert_details = cert['Certificate']
                
                not_after = cert_details['NotAfter']
                days_until_expiry = (not_after - now).days
                
                # Alert if expiring within 30 days
                if days_until_expiry < 30:
                    severity = 'critical' if days_until_expiry < 7 else 'high' if days_until_expiry < 14 else 'medium'
                    
                    self.issues.append({
                        'type': 'reliability',
                        'category': 'certificate_expiration',
                        'severity': severity,
                        'resource_id': cert_arn,
                        'resource_type': 'acm_certificate',
                        'title': f'Certificate expiring soon: {cert_details.get("DomainName")}',
                        'description': f'Certificate expires in {days_until_expiry} days',
                        'recommendation': 'Renew certificate before expiration to avoid service disruption.',
                        'evidence': {
                            'domain_name': cert_details.get('DomainName'),
                            'expiration_date': not_after.isoformat(),
                            'days_until_expiry': days_until_expiry
                        }
                    })
        
        except Exception as e:
            logger.error(f"Failed to check certificate expirations: {e}")
    
    # ==================== Helper Methods ====================
    
    def _estimate_days_until_full(
        self,
        free_storage_gb: float,
        total_storage_gb: float,
        growth_rate_gb_per_day: float = 1.0
    ) -> int:
        """
        Estimate days until storage is full
        
        Args:
            free_storage_gb: Current free storage in GB
            total_storage_gb: Total allocated storage in GB
            growth_rate_gb_per_day: Estimated growth rate (default 1GB/day)
        
        Returns:
            Estimated days until full
        """
        if growth_rate_gb_per_day <= 0:
            return 999  # Unknown
        
        days = int(free_storage_gb / growth_rate_gb_per_day)
        return max(0, days)
