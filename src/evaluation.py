"""
Evaluation Script for Zombie Container Detection

This script evaluates the performance of the zombie container detection tool
against known test scenarios.
"""

import argparse
import logging
import time
import pandas as pd
import numpy as np
from typing import Dict, List, Any
from sklearn.metrics import precision_recall_fscore_support, confusion_matrix

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
        description="Evaluate zombie container detection performance"
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
        "--output",
        default="evaluation_results.csv",
        help="Output file for evaluation results"
    )
    
    return parser.parse_args()

def get_ground_truth():
    """
    Define the ground truth for test scenarios.
    
    Returns:
        Dictionary mapping container names to their true classification
    """
    return {
        "normal-container": "normal",
        "zombie-low-cpu": "zombie",
        "zombie-memory-leak": "zombie",
        "zombie-stuck-process": "zombie",
        "zombie-network-timeout": "zombie",
        "zombie-resource-imbalance": "zombie"
    }

def evaluate_detector(detector: ZombieDetector, ground_truth: Dict[str, str], 
                     duration_minutes: int, threshold: float) -> Dict[str, Any]:
    """
    Evaluate the detector against ground truth.
    
    Args:
        detector: ZombieDetector instance
        ground_truth: Dictionary mapping container names to their true classification
        duration_minutes: Duration to analyze metrics for
        threshold: Score threshold for zombie classification
        
    Returns:
        Dictionary containing evaluation metrics
    """
    results = []
    
    # Get all containers in the test-scenarios namespace
    containers = detector._get_containers()
    test_containers = [c for c in containers if c["namespace"] == "test-scenarios"]
    
    y_true = []
    y_pred = []
    scores = []
    
    # Analyze each container
    for container in test_containers:
        pod = container["pod"]
        container_name = container["container"]
        
        # Extract deployment name from pod name (remove random suffix)
        deployment_name = "-".join(pod.split("-")[:-2]) if "-" in pod else pod
        
        # Skip if not in ground truth
        if deployment_name not in ground_truth:
            continue
        
        # Get container metrics
        metrics = detector.metrics_collector.get_container_metrics(
            "test-scenarios", pod, container_name, duration_minutes
        )
        
        # Get resource limits
        resource_limits = detector.metrics_collector.get_container_resource_limits(
            "test-scenarios", pod, container_name
        )
        
        # Analyze container using heuristics
        result = detector.heuristics.analyze_container(metrics, resource_limits)
        
        # Record results
        true_class = 1 if ground_truth[deployment_name] == "zombie" else 0
        pred_class = 1 if result["score"] >= threshold else 0
        
        y_true.append(true_class)
        y_pred.append(pred_class)
        scores.append(result["score"])
        
        results.append({
            "deployment": deployment_name,
            "pod": pod,
            "container": container_name,
            "true_class": ground_truth[deployment_name],
            "pred_class": "zombie" if pred_class == 1 else "normal",
            "score": result["score"],
            "correct": true_class == pred_class
        })
    
    # Calculate metrics
    if len(y_true) > 0 and len(y_pred) > 0:
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_true, y_pred, average='binary'
        )
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
        
        metrics = {
            "accuracy": (tp + tn) / (tp + tn + fp + fn),
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "true_positives": tp,
            "false_positives": fp,
            "true_negatives": tn,
            "false_negatives": fn
        }
    else:
        metrics = {
            "accuracy": 0,
            "precision": 0,
            "recall": 0,
            "f1_score": 0,
            "true_positives": 0,
            "false_positives": 0,
            "true_negatives": 0,
            "false_negatives": 0
        }
    
    return {
        "results": results,
        "metrics": metrics
    }

def main():
    """Main entry point."""
    args = parse_args()
    
    # Create detector
    detector = ZombieDetector(
        prometheus_url=args.prometheus_url,
        namespace_exclude=["kube-system", "monitoring", "zombie-detector"]
    )
    
    # Get ground truth
    ground_truth = get_ground_truth()
    
    # Evaluate detector
    logger.info("Evaluating detector performance...")
    evaluation = evaluate_detector(
        detector, ground_truth, args.duration, args.threshold
    )
    
    # Print metrics
    metrics = evaluation["metrics"]
    logger.info("Evaluation metrics:")
    logger.info(f"  Accuracy: {metrics['accuracy']:.4f}")
    logger.info(f"  Precision: {metrics['precision']:.4f}")
    logger.info(f"  Recall: {metrics['recall']:.4f}")
    logger.info(f"  F1 Score: {metrics['f1_score']:.4f}")
    logger.info(f"  True Positives: {metrics['true_positives']}")
    logger.info(f"  False Positives: {metrics['false_positives']}")
    logger.info(f"  True Negatives: {metrics['true_negatives']}")
    logger.info(f"  False Negatives: {metrics['false_negatives']}")
    
    # Save results to CSV
    results_df = pd.DataFrame(evaluation["results"])
    results_df.to_csv(args.output, index=False)
    logger.info(f"Results saved to {args.output}")
    
    return 0

if __name__ == "__main__":
    main()
