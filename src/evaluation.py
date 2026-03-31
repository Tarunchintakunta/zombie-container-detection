"""
Evaluation script to measure detection accuracy against ground-truth test scenarios.
Calculates accuracy, precision, recall, F1 score, and confusion matrix.
"""

import argparse
import csv
import json
import logging
import sys

from .detector import ZombieDetector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Ground truth: container name -> expected classification
GROUND_TRUTH = {
    "normal-web": "normal",
    "normal-batch": "normal",
    "zombie-low-cpu": "zombie",
    "zombie-memory-leak": "zombie",
    "zombie-stuck-process": "zombie",
    "zombie-network-timeout": "zombie",
    "zombie-resource-imbalance": "zombie",
}


def evaluate(prometheus_url: str, namespace: str = "test-scenarios",
             duration_minutes: int = 60) -> dict:
    """Run evaluation against ground truth test scenarios."""
    detector = ZombieDetector(
        prometheus_url=prometheus_url,
        duration_minutes=duration_minutes,
        exclude_namespaces=["kube-system", "kube-public", "kube-node-lease", "monitoring"],
    )

    results = detector.detect()

    # Filter to test namespace only
    test_containers = [
        c for c in results["containers"]
        if c["namespace"] == namespace
    ]

    if not test_containers:
        logger.error("No containers found in namespace '%s'", namespace)
        logger.info("Found namespaces: %s",
                     set(c["namespace"] for c in results["containers"]))
        return {"error": "no containers found in test namespace"}

    # Match against ground truth
    tp = fp = tn = fn = 0
    per_container = []

    for container in test_containers:
        name = container["container"]
        predicted = container["classification"]
        expected = GROUND_TRUTH.get(name)

        if expected is None:
            logger.warning("Container '%s' not in ground truth, skipping", name)
            continue

        # Binary classification: zombie/potential_zombie vs normal
        predicted_positive = predicted in ("zombie", "potential_zombie")
        actual_positive = expected == "zombie"

        if actual_positive and predicted_positive:
            tp += 1
            match = True
        elif not actual_positive and not predicted_positive:
            tn += 1
            match = True
        elif not actual_positive and predicted_positive:
            fp += 1
            match = False
        else:  # actual_positive and not predicted_positive
            fn += 1
            match = False

        per_container.append({
            "container": name,
            "expected": expected,
            "predicted": predicted,
            "score": container["score"],
            "correct": match,
            "rules": container.get("rules", {}),
        })

    # Calculate metrics
    total = tp + tn + fp + fn
    accuracy = (tp + tn) / total if total > 0 else 0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0

    evaluation = {
        "metrics": {
            "accuracy": round(accuracy, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "false_positive_rate": round(fpr, 4),
        },
        "confusion_matrix": {
            "true_positives": tp,
            "true_negatives": tn,
            "false_positives": fp,
            "false_negatives": fn,
        },
        "per_container": per_container,
        "total_containers": total,
    }

    return evaluation


def print_evaluation(evaluation: dict):
    """Print evaluation results in a readable format."""
    if "error" in evaluation:
        print(f"Error: {evaluation['error']}")
        return

    print("=" * 60)
    print("EVALUATION RESULTS")
    print("=" * 60)

    m = evaluation["metrics"]
    print(f"\nAccuracy:           {m['accuracy']:.2%}")
    print(f"Precision:          {m['precision']:.2%}")
    print(f"Recall:             {m['recall']:.2%}")
    print(f"F1 Score:           {m['f1_score']:.2%}")
    print(f"False Positive Rate: {m['false_positive_rate']:.2%}")

    cm = evaluation["confusion_matrix"]
    print(f"\nConfusion Matrix:")
    print(f"  True Positives:  {cm['true_positives']}")
    print(f"  True Negatives:  {cm['true_negatives']}")
    print(f"  False Positives: {cm['false_positives']}")
    print(f"  False Negatives: {cm['false_negatives']}")

    print(f"\nPer-Container Results:")
    print(f"{'Container':<30} {'Expected':<12} {'Predicted':<18} {'Score':>8} {'Correct':>8}")
    print("-" * 80)
    for c in evaluation["per_container"]:
        correct_str = "YES" if c["correct"] else "NO"
        print(f"{c['container']:<30} {c['expected']:<12} {c['predicted']:<18} {c['score']:>7.1f} {correct_str:>8}")

    target = 90.0
    actual = m["accuracy"] * 100
    print(f"\nTarget accuracy: {target}% | Actual: {actual:.1f}% | {'PASS' if actual >= target else 'BELOW TARGET'}")


def save_csv(evaluation: dict, filename: str = "evaluation_results.csv"):
    """Save per-container results to CSV."""
    if "per_container" not in evaluation:
        return
    with open(filename, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "container", "expected", "predicted", "score", "correct",
        ])
        writer.writeheader()
        for c in evaluation["per_container"]:
            writer.writerow({
                "container": c["container"],
                "expected": c["expected"],
                "predicted": c["predicted"],
                "score": c["score"],
                "correct": c["correct"],
            })
    logger.info("Results saved to %s", filename)


def main():
    parser = argparse.ArgumentParser(description="Evaluate zombie detector accuracy")
    parser.add_argument(
        "--prometheus-url",
        default="http://prometheus-server.monitoring.svc.cluster.local:9090",
    )
    parser.add_argument("--namespace", default="test-scenarios")
    parser.add_argument("--duration", type=int, default=60)
    parser.add_argument("--output-csv", default="evaluation_results.csv")
    parser.add_argument("--output-json", default="")
    args = parser.parse_args()

    evaluation = evaluate(args.prometheus_url, args.namespace, args.duration)
    print_evaluation(evaluation)
    save_csv(evaluation, args.output_csv)

    if args.output_json:
        with open(args.output_json, "w") as f:
            json.dump(evaluation, f, indent=2)

    # Exit 0 if accuracy >= 90%, else 1
    if "metrics" in evaluation and evaluation["metrics"]["accuracy"] >= 0.90:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
