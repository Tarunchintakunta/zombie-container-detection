"""
Prometheus metrics exporter for zombie detection results.
Exposes zombie scores as Prometheus metrics so Grafana can visualise them.
"""

import logging
import threading
from prometheus_client import Gauge, Info, start_http_server

logger = logging.getLogger(__name__)

# Prometheus metrics
ZOMBIE_SCORE = Gauge(
    "zombie_container_score",
    "Composite zombie score for a container (0-100)",
    ["namespace", "pod", "container"],
)

ZOMBIE_RULE_SCORE = Gauge(
    "zombie_container_rule_score",
    "Individual heuristic rule score (0-1)",
    ["namespace", "pod", "container", "rule"],
)

ZOMBIE_CLASSIFICATION = Gauge(
    "zombie_container_is_zombie",
    "Whether container is classified as zombie (1) or not (0)",
    ["namespace", "pod", "container"],
)

ZOMBIE_POTENTIAL = Gauge(
    "zombie_container_is_potential",
    "Whether container is classified as potential zombie (1) or not (0)",
    ["namespace", "pod", "container"],
)

DETECTION_TOTAL = Gauge(
    "zombie_detection_total_containers",
    "Total number of containers analysed in last detection run",
)

DETECTION_ZOMBIES = Gauge(
    "zombie_detection_zombies_count",
    "Number of zombies detected in last run",
)

DETECTION_POTENTIAL = Gauge(
    "zombie_detection_potential_count",
    "Number of potential zombies detected in last run",
)

DETECTION_NORMAL = Gauge(
    "zombie_detection_normal_count",
    "Number of normal containers in last run",
)


def start_metrics_server(port: int = 8080):
    """Start the Prometheus metrics HTTP server in a background thread."""
    start_http_server(port)
    logger.info("Prometheus metrics server started on port %d", port)


def update_metrics(results: dict):
    """Update Prometheus metrics with detection results."""
    if not results or "containers" not in results:
        return

    # Update summary metrics
    summary = results.get("summary", {})
    DETECTION_TOTAL.set(summary.get("total", 0))
    DETECTION_ZOMBIES.set(summary.get("zombies", 0))
    DETECTION_POTENTIAL.set(summary.get("potential_zombies", 0))
    DETECTION_NORMAL.set(summary.get("normal", 0))

    # Update per-container metrics
    for c in results["containers"]:
        ns = c.get("namespace", "")
        pod = c.get("pod", "")
        container = c.get("container", "")
        labels = [ns, pod, container]

        # Composite score
        ZOMBIE_SCORE.labels(*labels).set(c.get("score", 0))

        # Classification flags
        classification = c.get("classification", "normal")
        ZOMBIE_CLASSIFICATION.labels(*labels).set(1 if classification == "zombie" else 0)
        ZOMBIE_POTENTIAL.labels(*labels).set(1 if classification == "potential_zombie" else 0)

        # Per-rule scores
        rules = c.get("rules", {})
        for rule_name, rule_score in rules.items():
            ZOMBIE_RULE_SCORE.labels(ns, pod, container, rule_name).set(rule_score)

    logger.info(
        "Metrics updated: %d containers (%d zombie, %d potential, %d normal)",
        summary.get("total", 0),
        summary.get("zombies", 0),
        summary.get("potential_zombies", 0),
        summary.get("normal", 0),
    )
