"""
Zombie Container Detection CLI

This module provides a command-line interface for detecting zombie containers
in Kubernetes clusters.
"""

import argparse
import json
import logging
import sys
import time
from typing import Dict, List, Any

from detector.detector import ZombieDetector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Detect zombie containers in Kubernetes clusters"
    )
    
    parser.add_argument(
        "--prometheus-url",
        default="http://prometheus.monitoring:9090",
        help="URL of the Prometheus server"
    )
    
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Duration in minutes to analyze metrics for"
    )
    
    parser.add_argument(
        "--threshold",
        type=float,
        default=70.0,
        help="Score threshold for zombie classification"
    )
    
    parser.add_argument(
        "--exclude-namespaces",
        default="kube-system,monitoring",
        help="Comma-separated list of namespaces to exclude"
    )
    
    parser.add_argument(
        "--output",
        choices=["json", "text"],
        default="text",
        help="Output format"
    )
    
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Run in continuous mode with periodic checks"
    )
    
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="Interval in seconds between checks in continuous mode"
    )
    
    parser.add_argument(
        "--details",
        action="store_true",
        help="Show detailed analysis for each zombie container"
    )
    
    return parser.parse_args()

def format_output(zombies: List[Dict[str, Any]], output_format: str, show_details: bool) -> str:
    """Format the output based on the specified format."""
    if output_format == "json":
        return json.dumps(zombies, indent=2)
    
    # Text format
    if not zombies:
        return "No zombie containers detected."
    
    lines = ["Zombie Containers:"]
    for zombie in zombies:
        container = zombie["container"]
        lines.append(f"\n{container['namespace']}/{container['pod']}/{container['container']}")
        lines.append(f"  Score: {zombie['score']:.2f}")
        lines.append(f"  Node: {container.get('node', 'N/A')}")
        
        if show_details:
            lines.append("  Rule Scores:")
            for rule, score in zombie["rule_scores"].items():
                lines.append(f"    {rule}: {score:.2f}")
            
            lines.append("  Details:")
            for rule, details in zombie["details"].items():
                if details:
                    lines.append(f"    {rule}:")
                    for key, value in details.items():
                        lines.append(f"      {key}: {value}")
    
    return "\n".join(lines)

def main():
    """Main entry point."""
    args = parse_args()
    
    # Parse excluded namespaces
    excluded_namespaces = args.exclude_namespaces.split(",") if args.exclude_namespaces else []
    
    # Create detector
    detector = ZombieDetector(
        prometheus_url=args.prometheus_url,
        namespace_exclude=excluded_namespaces
    )
    
    # Run detection
    if args.continuous:
        logger.info(f"Running in continuous mode with {args.interval}s interval")
        try:
            while True:
                zombies = detector.detect_zombies(
                    duration_minutes=args.duration,
                    score_threshold=args.threshold
                )
                
                output = format_output(zombies, args.output, args.details)
                print(output)
                print(f"\nNext check in {args.interval} seconds...")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
    else:
        zombies = detector.detect_zombies(
            duration_minutes=args.duration,
            score_threshold=args.threshold
        )
        
        output = format_output(zombies, args.output, args.details)
        print(output)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
