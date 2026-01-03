#!/usr/bin/env python3
"""
Quick Scan Script - Run CloudGuard scan from command line
Usage: python scripts/quick_scan.py [--region us-east-1] [--output json]
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.aws_client import AWSClientManager
from app.modules.cost import CostScanner
from app.modules.security import SecurityScanner
from app.modules.reliability import ReliabilityScanner


async def run_scan(region: str, output_format: str):
    """Run all scanners and output results"""
    print(f"\n{'='*60}")
    print(f"  CloudGuard Quick Scan - Region: {region}")
    print(f"{'='*60}\n")
    
    aws = AWSClientManager(region=region)
    
    all_findings = []
    
    # Cost Scan
    print("📊 Scanning for cost optimization opportunities...")
    cost_scanner = CostScanner(aws)
    cost_findings = await cost_scanner.scan_all([region])
    all_findings.extend(cost_findings)
    print(f"   Found {len(cost_findings)} cost findings")
    
    # Security Scan
    print("🔒 Scanning for security misconfigurations...")
    security_scanner = SecurityScanner(aws)
    security_findings = await security_scanner.scan_all([region])
    all_findings.extend(security_findings)
    print(f"   Found {len(security_findings)} security findings")
    
    # Reliability Scan
    print("⚡ Scanning for reliability issues...")
    reliability_scanner = ReliabilityScanner(aws)
    reliability_findings = await reliability_scanner.scan_all([region])
    all_findings.extend(reliability_findings)
    print(f"   Found {len(reliability_findings)} reliability findings")
    
    # Summary
    print(f"\n{'='*60}")
    print(f"  SCAN COMPLETE - Total Findings: {len(all_findings)}")
    print(f"{'='*60}")
    
    # Count by severity
    severity_counts = {}
    for finding in all_findings:
        sev = finding.severity.value
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
    
    print("\nFindings by Severity:")
    for sev in ["critical", "high", "medium", "low", "info"]:
        count = severity_counts.get(sev, 0)
        emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "info": "⚪"}
        if count > 0:
            print(f"  {emoji[sev]} {sev.upper()}: {count}")
    
    # Calculate potential savings
    total_savings = sum(f.estimated_savings or 0 for f in all_findings)
    if total_savings > 0:
        print(f"\n💰 Potential Monthly Savings: ${total_savings:,.2f}")
    
    # Output detailed findings
    if output_format == "json":
        print("\n" + "="*60)
        print("Detailed Findings (JSON):")
        print("="*60)
        findings_data = [f.model_dump() for f in all_findings]
        print(json.dumps(findings_data, indent=2, default=str))
    else:
        print("\n" + "="*60)
        print("Top Priority Findings:")
        print("="*60)
        
        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        sorted_findings = sorted(all_findings, key=lambda f: severity_order[f.severity.value])
        
        for finding in sorted_findings[:10]:
            sev = finding.severity.value.upper()
            cat = finding.category.value.upper()
            print(f"\n[{sev}] [{cat}] {finding.title}")
            print(f"   {finding.description}")
            print(f"   Recommendation: {finding.recommendation}")
            if finding.estimated_savings:
                print(f"   💰 Potential Savings: ${finding.estimated_savings:.2f}/mo")
    
    return all_findings


def main():
    parser = argparse.ArgumentParser(description="CloudGuard Quick Scan")
    parser.add_argument("--region", default="us-east-1", help="AWS region to scan")
    parser.add_argument("--output", choices=["text", "json"], default="text", help="Output format")
    args = parser.parse_args()
    
    try:
        asyncio.run(run_scan(args.region, args.output))
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure you have valid AWS credentials configured.")
        sys.exit(1)


if __name__ == "__main__":
    main()
