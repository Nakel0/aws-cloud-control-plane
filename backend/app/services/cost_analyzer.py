"""
Cost Analysis Service
Analyzes AWS cost data and identifies optimization opportunities
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import logging

from app.services.aws_client import AWSClient
from app.models import Account, Resource, Recommendation, RecommendationType, Priority

logger = logging.getLogger(__name__)


class CostAnalyzer:
    """
    AWS Cost Analyzer
    
    Identifies cost optimization opportunities:
    - Idle resources
    - Oversized resources
    - Orphaned resources
    - Reserved Instance recommendations
    """
    
    def __init__(self, aws_client: AWSClient):
        self.aws_client = aws_client
    
    def fetch_cost_data(
        self,
        start_date: datetime,
        end_date: datetime,
        granularity: str = "DAILY"
    ) -> List[Dict[str, Any]]:
        """
        Fetch cost and usage data from AWS Cost Explorer
        
        Args:
            start_date: Start date for cost data
            end_date: End date for cost data
            granularity: DAILY, MONTHLY, or HOURLY
        
        Returns:
            List of cost data points
        """
        try:
            ce = self.aws_client.get_client('ce', region='us-east-1')
            
            response = ce.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity=granularity,
                Metrics=['UnblendedCost', 'UsageQuantity'],
                GroupBy=[
                    {'Type': 'DIMENSION', 'Key': 'SERVICE'},
                    {'Type': 'DIMENSION', 'Key': 'USAGE_TYPE'}
                ]
            )
            
            cost_data = []
            for result in response.get('ResultsByTime', []):
                time_period = result['TimePeriod']
                
                for group in result.get('Groups', []):
                    service = group['Keys'][0]
                    usage_type = group['Keys'][1]
                    
                    cost = Decimal(group['Metrics']['UnblendedCost']['Amount'])
                    usage = Decimal(group['Metrics']['UsageQuantity']['Amount'])
                    
                    cost_data.append({
                        'time': time_period['Start'],
                        'service': service,
                        'usage_type': usage_type,
                        'cost': cost,
                        'usage_amount': usage,
                        'currency': group['Metrics']['UnblendedCost']['Unit']
                    })
            
            logger.info(f"Fetched {len(cost_data)} cost data points")
            return cost_data
            
        except Exception as e:
            logger.error(f"Failed to fetch cost data: {e}")
            raise
    
    def detect_idle_ec2_instances(self) -> List[Dict[str, Any]]:
        """
        Detect idle EC2 instances (low CPU utilization)
        
        Returns:
            List of idle instances with recommendations
        """
        recommendations = []
        
        try:
            ec2 = self.aws_client.get_client('ec2')
            cloudwatch = self.aws_client.get_client('cloudwatch')
            
            # Get all running instances
            response = ec2.describe_instances(
                Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
            )
            
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    instance_id = instance['InstanceId']
                    instance_type = instance['InstanceType']
                    
                    # Get CPU utilization for last 7 days
                    cpu_stats = cloudwatch.get_metric_statistics(
                        Namespace='AWS/EC2',
                        MetricName='CPUUtilization',
                        Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                        StartTime=datetime.utcnow() - timedelta(days=7),
                        EndTime=datetime.utcnow(),
                        Period=3600,  # 1 hour
                        Statistics=['Average', 'Maximum']
                    )
                    
                    if cpu_stats['Datapoints']:
                        avg_cpu = sum(dp['Average'] for dp in cpu_stats['Datapoints']) / len(cpu_stats['Datapoints'])
                        max_cpu = max(dp['Maximum'] for dp in cpu_stats['Datapoints'])
                        
                        # Idle if avg CPU < 5% and max CPU < 20%
                        if avg_cpu < 5.0 and max_cpu < 20.0:
                            # Calculate monthly cost (simplified)
                            monthly_cost = self._estimate_ec2_cost(instance_type)
                            
                            recommendations.append({
                                'resource_id': instance_id,
                                'resource_type': 'ec2_instance',
                                'type': RecommendationType.COST_OPTIMIZATION,
                                'priority': Priority.HIGH,
                                'title': f'Idle EC2 instance: {instance_id}',
                                'description': f'Instance has been running with <5% CPU for 7 days',
                                'potential_savings': monthly_cost,
                                'confidence': 0.95,
                                'evidence': {
                                    'avg_cpu': round(avg_cpu, 2),
                                    'max_cpu': round(max_cpu, 2),
                                    'days_monitored': 7,
                                    'instance_type': instance_type
                                },
                                'actions': [
                                    {
                                        'type': 'stop_instance',
                                        'description': 'Stop the instance',
                                        'risk': 'low'
                                    },
                                    {
                                        'type': 'terminate_instance',
                                        'description': 'Terminate after creating snapshot',
                                        'risk': 'medium'
                                    }
                                ]
                            })
            
            logger.info(f"Found {len(recommendations)} idle EC2 instances")
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to detect idle EC2 instances: {e}")
            return []
    
    def detect_unattached_ebs_volumes(self) -> List[Dict[str, Any]]:
        """
        Detect unattached EBS volumes
        
        Returns:
            List of unattached volumes with recommendations
        """
        recommendations = []
        
        try:
            ec2 = self.aws_client.get_client('ec2')
            
            # Get all volumes
            response = ec2.describe_volumes(
                Filters=[{'Name': 'status', 'Values': ['available']}]
            )
            
            for volume in response['Volumes']:
                volume_id = volume['VolumeId']
                size_gb = volume['Size']
                volume_type = volume['VolumeType']
                create_time = volume['CreateTime']
                
                # Calculate age
                age_days = (datetime.now(create_time.tzinfo) - create_time).days
                
                # Only recommend if unattached for > 30 days
                if age_days > 30:
                    # Calculate monthly cost
                    monthly_cost = self._estimate_ebs_cost(size_gb, volume_type)
                    
                    recommendations.append({
                        'resource_id': volume_id,
                        'resource_type': 'ebs_volume',
                        'type': RecommendationType.COST_OPTIMIZATION,
                        'priority': Priority.MEDIUM,
                        'title': f'Unattached EBS volume: {volume_id}',
                        'description': f'Volume has been unattached for {age_days} days',
                        'potential_savings': monthly_cost,
                        'confidence': 1.0,
                        'evidence': {
                            'size_gb': size_gb,
                            'volume_type': volume_type,
                            'age_days': age_days,
                            'created': create_time.isoformat()
                        },
                        'actions': [
                            {
                                'type': 'create_snapshot',
                                'description': 'Create snapshot before deletion',
                                'risk': 'low'
                            },
                            {
                                'type': 'delete_volume',
                                'description': 'Delete the volume',
                                'risk': 'low'
                            }
                        ]
                    })
            
            logger.info(f"Found {len(recommendations)} unattached EBS volumes")
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to detect unattached EBS volumes: {e}")
            return []
    
    def detect_unused_elastic_ips(self) -> List[Dict[str, Any]]:
        """
        Detect unused Elastic IP addresses
        
        Returns:
            List of unused EIPs with recommendations
        """
        recommendations = []
        
        try:
            ec2 = self.aws_client.get_client('ec2')
            
            # Get all Elastic IPs
            response = ec2.describe_addresses()
            
            for address in response['Addresses']:
                # Check if EIP is not associated with any instance
                if 'AssociationId' not in address:
                    public_ip = address['PublicIp']
                    allocation_id = address.get('AllocationId', 'N/A')
                    
                    # Unused EIPs cost $0.005/hour = ~$3.60/month
                    monthly_cost = 3.60
                    
                    recommendations.append({
                        'resource_id': allocation_id,
                        'resource_type': 'elastic_ip',
                        'type': RecommendationType.COST_OPTIMIZATION,
                        'priority': Priority.LOW,
                        'title': f'Unused Elastic IP: {public_ip}',
                        'description': 'Elastic IP is not associated with any instance',
                        'potential_savings': monthly_cost,
                        'confidence': 1.0,
                        'evidence': {
                            'public_ip': public_ip,
                            'allocation_id': allocation_id
                        },
                        'actions': [
                            {
                                'type': 'release_eip',
                                'description': 'Release the Elastic IP',
                                'risk': 'low'
                            }
                        ]
                    })
            
            logger.info(f"Found {len(recommendations)} unused Elastic IPs")
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to detect unused Elastic IPs: {e}")
            return []
    
    def analyze_reserved_instance_opportunities(self) -> List[Dict[str, Any]]:
        """
        Identify instances that would benefit from Reserved Instance pricing
        
        Returns:
            List of RI recommendations
        """
        recommendations = []
        
        try:
            ec2 = self.aws_client.get_client('ec2')
            
            # Get all running instances
            response = ec2.describe_instances(
                Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
            )
            
            # Track instance types and their running duration
            instance_tracker = {}
            
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    instance_id = instance['InstanceId']
                    instance_type = instance['InstanceType']
                    launch_time = instance['LaunchTime']
                    
                    # Calculate running duration
                    running_days = (datetime.now(launch_time.tzinfo) - launch_time).days
                    
                    # Recommend RI if running for > 30 days
                    if running_days > 30:
                        # Calculate potential savings (RI typically saves 30-40%)
                        on_demand_cost = self._estimate_ec2_cost(instance_type)
                        ri_cost = on_demand_cost * 0.65  # 35% savings
                        monthly_savings = on_demand_cost - ri_cost
                        
                        recommendations.append({
                            'resource_id': instance_id,
                            'resource_type': 'ec2_instance',
                            'type': RecommendationType.COST_OPTIMIZATION,
                            'priority': Priority.HIGH,
                            'title': f'Reserved Instance opportunity: {instance_type}',
                            'description': f'Instance has been running for {running_days} days',
                            'potential_savings': monthly_savings,
                            'confidence': 0.90,
                            'evidence': {
                                'instance_type': instance_type,
                                'running_days': running_days,
                                'on_demand_cost': on_demand_cost,
                                'ri_cost': ri_cost,
                                'savings_percentage': '35%'
                            },
                            'actions': [
                                {
                                    'type': 'purchase_ri',
                                    'description': 'Purchase 1-year Reserved Instance',
                                    'risk': 'low'
                                }
                            ]
                        })
            
            logger.info(f"Found {len(recommendations)} RI opportunities")
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to analyze RI opportunities: {e}")
            return []
    
    def _estimate_ec2_cost(self, instance_type: str) -> Decimal:
        """
        Estimate monthly cost for EC2 instance type
        
        This is a simplified calculation. In production, use AWS Pricing API.
        """
        # Simplified pricing (actual prices vary by region)
        hourly_rates = {
            't2.micro': 0.0116,
            't2.small': 0.023,
            't2.medium': 0.0464,
            't3.micro': 0.0104,
            't3.small': 0.0208,
            't3.medium': 0.0416,
            'm5.large': 0.096,
            'm5.xlarge': 0.192,
            'c5.large': 0.085,
            'r5.large': 0.126,
        }
        
        hourly_rate = hourly_rates.get(instance_type, 0.10)  # Default rate
        monthly_cost = Decimal(str(hourly_rate * 730))  # 730 hours/month avg
        
        return monthly_cost
    
    def _estimate_ebs_cost(self, size_gb: int, volume_type: str) -> Decimal:
        """
        Estimate monthly cost for EBS volume
        """
        # Simplified pricing (actual prices vary by region)
        per_gb_month = {
            'gp2': 0.10,
            'gp3': 0.08,
            'io1': 0.125,
            'io2': 0.125,
            'st1': 0.045,
            'sc1': 0.025,
        }
        
        rate = per_gb_month.get(volume_type, 0.10)
        monthly_cost = Decimal(str(size_gb * rate))
        
        return monthly_cost
