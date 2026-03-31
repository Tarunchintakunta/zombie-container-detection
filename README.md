# Heuristic-Based Zombie Container Detection for Kubernetes

A lightweight, transparent, rule-based system for detecting zombie containers in Kubernetes clusters. Designed for resource optimisation with >90% detection accuracy and low computational overhead.

**Author:** Anurag Baiju (23409223) — MSc Cloud Computing, National College of Ireland

## Problem

Zombie containers are containers that consume computational resources (CPU, memory) without performing useful work. Studies show up to 50% of cloud spend is wasted on inefficient resource utilisation (StormForge, 2021). Kubernetes' default metrics cannot distinguish active containers from zombies, leading to resource waste.

## Approach

This system uses 5 weighted heuristic rules that analyse temporal patterns in CPU, memory, and network metrics collected from Prometheus:

| Rule | Weight | What it Detects |
|------|--------|-----------------|
| Rule 1: Sustained Low CPU | 35% | CPU <5% for >30min with memory allocated and no network |
| Rule 2: Memory Leak | 25% | Memory increasing >5% over 1hr with CPU <1% |
| Rule 3: Stuck Process | 15% | Brief CPU spikes then long idle, repeated 3+ times |
| Rule 4: Network Timeout | 15% | Periodic low-volume network retries to dead services |
| Rule 5: Resource Imbalance | 10% | High memory allocation (>500MB) with <10% usage and <1% CPU |

Each container receives a composite score (0-100):
- **Score >= 60**: Zombie
- **Score 30-60**: Potential Zombie
- **Score < 30**: Normal

## Architecture

```
Kubernetes Cluster
├── monitoring namespace
│   ├── Prometheus (scrapes cAdvisor metrics every 15s)
│   └── Grafana (auto-provisioned dashboard for real-time visibility)
├── test-scenarios namespace
│   ├── normal-web (active web server)
│   ├── normal-batch (periodic batch processor)
│   ├── zombie-low-cpu (idle with memory held)
│   ├── zombie-memory-leak (gradual memory growth)
│   ├── zombie-stuck-process (retry loop pattern)
│   ├── zombie-network-timeout (dead service retries)
│   └── zombie-resource-imbalance (over-provisioned idle)
└── zombie-detector namespace
    └── Detector (queries Prometheus, applies 5 rules, exports metrics)
```

## Extra Feature: Grafana Dashboard

Beyond the paper requirements, this system includes an **auto-provisioned Grafana dashboard** that provides real-time operational visibility — a gap not addressed by either Anemogiannis et al. (2025) or Li et al. (2025).

The dashboard includes:
- **Detection Summary** — stat panels showing total containers, zombies, potential zombies, and normal counts
- **Zombie Scores Over Time** — time series chart with threshold lines (60=zombie, 30=potential)
- **Per-Rule Breakdown** — 5 individual charts showing each heuristic rule's score over time
- **Raw Container Metrics** — CPU usage, memory usage, and network activity for test containers
- **Classification Distribution** — donut chart showing zombie/potential/normal proportions

Access: `kubectl port-forward -n monitoring svc/grafana 3000:3000` then open http://localhost:3000 (admin/admin)

## Prerequisites

- AWS account with EKS permissions (or any Kubernetes cluster)
- `aws` CLI, `eksctl`, `kubectl`, `docker` installed
- Python 3.8+

## Quick Start

### 1. Clone and install dependencies

```bash
git clone <repo-url>
cd zombie-container-detection
pip install -r requirements.txt
```

### 2. Deploy to Kubernetes (AWS EKS)

**Option A: Full setup (creates EKS cluster)**
```bash
chmod +x setup.sh
./setup.sh
```

**Option B: Deploy to existing cluster**
```bash
chmod +x deploy.sh
./deploy.sh
```

### 3. Wait for metrics (30-60 minutes)

The test scenarios need time to generate enough metric data for accurate detection.

```bash
# Check test pods are running
kubectl get pods -n test-scenarios

# Check Prometheus is collecting metrics
kubectl port-forward -n monitoring svc/prometheus-server 9090:9090 &
# Open http://localhost:9090 and query: container_cpu_usage_seconds_total
```

### 4. Access Grafana Dashboard

```bash
kubectl port-forward -n monitoring svc/grafana 3000:3000 &
# Open http://localhost:3000 (login: admin/admin)
# Dashboard is auto-loaded: "Zombie Container Detection Dashboard"
```

### 5. Run the detector

```bash
# Port-forward Prometheus
kubectl port-forward -n monitoring svc/prometheus-server 9090:9090 &

# One-shot detection with details
python -m src.main --prometheus-url=http://localhost:9090 --details

# JSON output
python -m src.main --prometheus-url=http://localhost:9090 --output=json
```

### 6. Run evaluation

```bash
python -m src.evaluation --prometheus-url=http://localhost:9090
```

This compares detections against ground truth and reports accuracy, precision, recall, and F1 score.

## CLI Options

```
python -m src.main [options]

  --prometheus-url URL     Prometheus server URL (default: cluster-internal)
  --duration MINUTES       Analysis window in minutes (default: 60)
  --threshold SCORE        Zombie threshold 0-100 (default: 70)
  --exclude-namespaces NS  Comma-separated namespaces to skip
  --output {text,json}     Output format (default: text)
  --details                Show per-rule breakdown
  --metrics-port PORT      Prometheus exporter port (default: 8080)
  --continuous             Run in continuous monitoring mode
  --interval SECONDS       Interval between checks (default: 300)
```

## Project Structure

```
zombie-container-detection/
├── src/
│   ├── main.py              # CLI entry point
│   ├── detector.py           # Detection orchestrator
│   ├── heuristics.py         # 5 heuristic rules engine
│   ├── metrics_collector.py  # Prometheus PromQL queries
│   ├── exporter.py           # Prometheus metrics exporter for Grafana
│   └── evaluation.py         # Accuracy evaluation
├── kubernetes/
│   ├── namespaces.yaml       # Namespace definitions
│   ├── rbac.yaml             # ServiceAccount & ClusterRole
│   ├── prometheus/           # Prometheus deployment
│   ├── grafana/              # Grafana with auto-provisioned dashboard
│   ├── detector/             # Detector deployment + service
│   └── test-scenarios/       # 7 test pods (2 normal + 5 zombie)
├── Dockerfile                # Container image for detector
├── setup.sh                  # Full AWS EKS setup
├── deploy.sh                 # Deploy to existing cluster
├── cleanup.sh                # Remove all resources
└── docs/                     # Paper critical reviews
```

## Cleanup

```bash
# Remove deployed resources
chmod +x cleanup.sh
./cleanup.sh

# Also delete the EKS cluster
DELETE_CLUSTER=true ./cleanup.sh
```
