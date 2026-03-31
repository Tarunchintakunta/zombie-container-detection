# Heuristic-Based Zombie Container Detection for Kubernetes

A lightweight, transparent, rule-based system for detecting zombie containers in Kubernetes clusters. Designed for resource optimisation with >90% detection accuracy and low computational overhead.

**Author:** Anurag Baiju (23409223) — MSc Cloud Computing, National College of Ireland

---

## Table of Contents

1. [What is This Project?](#what-is-this-project)
2. [How It Works](#how-it-works)
3. [Architecture](#architecture)
4. [Extra Feature: Grafana Dashboard](#extra-feature-grafana-dashboard)
5. [Prerequisites — Install Everything You Need](#prerequisites--install-everything-you-need)
6. [Step-by-Step Setup and Deployment](#step-by-step-setup-and-deployment)
7. [Running the Detector](#running-the-detector)
8. [Running the Evaluation](#running-the-evaluation)
9. [Viewing the Grafana Dashboard](#viewing-the-grafana-dashboard)
10. [CLI Options](#cli-options)
11. [Project Structure](#project-structure)
12. [Cleanup — Delete Everything When Done](#cleanup--delete-everything-when-done)
13. [Troubleshooting](#troubleshooting)

---

## What is This Project?

Zombie containers are containers running inside a Kubernetes cluster that **consume resources (CPU, memory) without doing any useful work**. They waste money and slow down other applications. Studies show up to 50% of cloud spending is wasted on idle or zombie containers (StormForge, 2021).

Kubernetes does not have a built-in way to detect zombies. This project solves that problem using **5 heuristic rules** (simple if-then logic) that analyse CPU, memory, and network patterns over time.

---

## How It Works

The system uses **5 weighted rules** that analyse temporal patterns in CPU, memory, and network metrics collected from Prometheus:

| Rule | Weight | What it Detects |
|------|--------|-----------------|
| Rule 1: Sustained Low CPU | 35% | CPU <5% for >30min with memory allocated and no network |
| Rule 2: Memory Leak | 25% | Memory increasing >5% over 1hr with CPU <1% |
| Rule 3: Stuck Process | 15% | Brief CPU spikes then long idle, repeated 3+ times |
| Rule 4: Network Timeout | 15% | Very low CPU with persistent low-volume network retries |
| Rule 5: Resource Imbalance | 10% | High memory allocation (>500MB) with <10% usage and <1% CPU |

Each container receives a **composite score (0-100)**:
- **Score >= 60**: Zombie (definitely wasting resources)
- **Score 30-60**: Potential Zombie (suspicious, needs attention)
- **Score < 30**: Normal (doing useful work)

---

## Architecture

```
Kubernetes Cluster (AWS EKS)
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

---

## Extra Feature: Grafana Dashboard

Beyond the paper requirements, this system includes an **auto-provisioned Grafana dashboard** that provides real-time operational visibility — a gap not addressed by either Anemogiannis et al. (2025) or Li et al. (2025).

The dashboard includes:
- **Detection Summary** — stat panels showing total containers, zombies, potential zombies, and normal counts
- **Zombie Scores Over Time** — time series chart with threshold lines (60=zombie, 30=potential)
- **Per-Rule Breakdown** — 5 individual charts showing each heuristic rule's score over time
- **Raw Container Metrics** — CPU usage, memory usage, and network activity for test containers
- **Classification Distribution** — donut chart showing zombie/potential/normal proportions

---

## Prerequisites — Install Everything You Need

You need to install the following tools on your computer. Follow each step carefully.

### 1. Install Python (version 3.8 or higher)

**Check if already installed:**
```bash
python --version
```
If it shows `Python 3.8` or higher, skip this step.

**If not installed:**
- Go to https://www.python.org/downloads/
- Download and install Python 3.12 or latest
- During installation, **check the box "Add Python to PATH"**

### 2. Install AWS CLI

The AWS CLI lets you interact with Amazon Web Services from the command line.

**Check if already installed:**
```bash
aws --version
```

**If not installed:**
- Go to https://aws.amazon.com/cli/
- Download the installer for your OS (Windows/Mac/Linux)
- Run the installer and follow the prompts
- After installation, close and reopen your terminal

### 3. Install kubectl

kubectl is the command-line tool for Kubernetes.

**Check if already installed:**
```bash
kubectl version --client
```

**If not installed:**
- **Windows:** Download from https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/
  ```bash
  curl -LO "https://dl.k8s.io/release/v1.29.0/bin/windows/amd64/kubectl.exe"
  ```
  Move `kubectl.exe` to a folder in your PATH (e.g., `C:\Windows\System32\`)

- **Mac:**
  ```bash
  brew install kubectl
  ```

- **Linux:**
  ```bash
  curl -LO "https://dl.k8s.io/release/v1.29.0/bin/linux/amd64/kubectl"
  chmod +x kubectl
  sudo mv kubectl /usr/local/bin/
  ```

### 4. Install eksctl

eksctl is a tool to create and manage EKS (Kubernetes) clusters on AWS.

**Check if already installed:**
```bash
eksctl version
```

**If not installed:**
- **Windows:** Download from https://eksctl.io/installation/
  ```bash
  curl -sLO "https://github.com/eksctl-io/eksctl/releases/latest/download/eksctl_Windows_amd64.zip"
  unzip eksctl_Windows_amd64.zip
  ```
  Move `eksctl.exe` to a folder in your PATH

- **Mac:**
  ```bash
  brew install eksctl
  ```

- **Linux:**
  ```bash
  curl -sLO "https://github.com/eksctl-io/eksctl/releases/latest/download/eksctl_Linux_amd64.tar.gz"
  tar -xzf eksctl_Linux_amd64.tar.gz
  sudo mv eksctl /usr/local/bin/
  ```

### 5. Install Docker

Docker is needed to build the detector container image.

**Check if already installed:**
```bash
docker --version
```

**If not installed:**
- Go to https://www.docker.com/products/docker-desktop/
- Download Docker Desktop for your OS
- Install and start Docker Desktop
- Make sure Docker Desktop is **running** (you should see the whale icon in your taskbar)

### 6. Install Git (if not already installed)

```bash
git --version
```

If not installed, download from https://git-scm.com/downloads

---

## Step-by-Step Setup and Deployment

### Step 1: Configure AWS Credentials

You need an AWS Access Key and Secret Key. If you are sharing an AWS account with classmates, your instructor will provide these.

**Run this command and enter your credentials when prompted:**
```bash
aws configure
```

It will ask you 4 things:
```
AWS Access Key ID [None]: <paste your access key here>
AWS Secret Access Key [None]: <paste your secret key here>
Default region name [None]: us-east-1
Default output format [None]: json
```

**Verify it works:**
```bash
aws sts get-caller-identity
```
You should see your AWS account number. If you get an error, your credentials are wrong — ask your instructor.

> **IMPORTANT:** If someone else has previously configured AWS on the same machine, you may need to clear old credentials first:
> - **Windows:** Delete the file `C:\Users\<YourName>\.aws\credentials` and run `aws configure` again
> - **Mac/Linux:** Delete the file `~/.aws/credentials` and run `aws configure` again

### Step 2: Clone the Project

```bash
git clone <your-repo-url>
cd zombie-container-detection
```

### Step 3: Install Python Dependencies

```bash
pip install -r requirements.txt
```

This installs: `requests`, `numpy`, `pandas`, `prometheus_client`, and `kubernetes` Python packages.

### Step 4: Create the EKS Cluster

> **IMPORTANT — If sharing an AWS account with classmates:**
> Each person MUST use a **unique cluster name** to avoid conflicts. Replace `YOUR_NAME` with your actual name (lowercase, no spaces):

```bash
export CLUSTER_NAME=zombie-detector-YOUR_NAME
```

For example: `export CLUSTER_NAME=zombie-detector-anurag`

**Now create the cluster (this takes 10-15 minutes, be patient):**
```bash
eksctl create cluster \
    --name $CLUSTER_NAME \
    --region us-east-1 \
    --node-type t3.medium \
    --nodes 2 \
    --nodes-min 1 \
    --nodes-max 3 \
    --managed
```

Wait until you see `EKS cluster "zombie-detector-YOUR_NAME" in "us-east-1" region is ready`.

**Update your kubectl config to connect to the new cluster:**
```bash
aws eks update-kubeconfig --name $CLUSTER_NAME --region us-east-1
```

**Verify you are connected:**
```bash
kubectl get nodes
```
You should see 2 nodes with status `Ready`. If you see an error, wait a minute and try again.

### Step 5: Deploy Namespaces and RBAC

```bash
kubectl apply -f kubernetes/namespaces.yaml
kubectl apply -f kubernetes/rbac.yaml
```

### Step 6: Deploy Prometheus (Metrics Collection)

```bash
kubectl apply -f kubernetes/prometheus/config.yaml
kubectl apply -f kubernetes/prometheus/deployment.yaml
```

**Wait for Prometheus to start (takes about 1 minute):**
```bash
kubectl wait --for=condition=available --timeout=120s deployment/prometheus-server -n monitoring
```

You should see: `deployment.apps/prometheus-server condition met`

### Step 7: Deploy Grafana (Dashboard)

```bash
kubectl apply -f kubernetes/grafana/datasource.yaml
kubectl apply -f kubernetes/grafana/dashboard-provider.yaml
kubectl apply -f kubernetes/grafana/dashboard.yaml
kubectl apply -f kubernetes/grafana/deployment.yaml
```

**Wait for Grafana to start:**
```bash
kubectl wait --for=condition=available --timeout=120s deployment/grafana -n monitoring
```

### Step 8: Deploy the 7 Test Scenarios

```bash
kubectl apply -f kubernetes/test-scenarios/
```

**Wait for all test pods to start:**
```bash
kubectl wait --for=condition=available --timeout=120s deployment --all -n test-scenarios
```

**Verify all 7 test pods are running:**
```bash
kubectl get pods -n test-scenarios
```

You should see 7 pods, all with status `Running`:
```
NAME                                         READY   STATUS    RESTARTS   AGE
normal-batch-xxx                             1/1     Running   0          1m
normal-web-xxx                               1/1     Running   0          1m
zombie-low-cpu-xxx                           1/1     Running   0          1m
zombie-memory-leak-xxx                       1/1     Running   0          1m
zombie-network-timeout-xxx                   1/1     Running   0          1m
zombie-resource-imbalance-xxx                1/1     Running   0          1m
zombie-stuck-process-xxx                     1/1     Running   0          1m
```

### Step 9: Build and Deploy the Detector

**9a. Build the Docker image:**
```bash
docker build -t zombie-detector:latest .
```

**9b. Create an ECR repository (container registry on AWS):**
```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=us-east-1

aws ecr create-repository --repository-name zombie-detector --region $REGION 2>/dev/null || true
```

**9c. Login to ECR:**
```bash
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"
```

You should see: `Login Succeeded`

**9d. Tag and push the image:**
```bash
docker tag zombie-detector:latest "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/zombie-detector:latest"
docker push "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/zombie-detector:latest"
```

Wait for the push to complete (you will see multiple layers being pushed).

**9e. Update the detector deployment with your ECR image:**
```bash
sed "s|810244486416.dkr.ecr.us-east-1.amazonaws.com/zombie-detector:latest|$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/zombie-detector:latest|" kubernetes/detector/deployment.yaml | kubectl apply -f -
```

**9f. Verify the detector is running:**
```bash
kubectl get pods -n zombie-detector
```

You should see 1 pod with status `Running`.

### Step 10: Wait for Metrics (IMPORTANT)

**You MUST wait 45-60 minutes** for the test scenarios to generate enough metric data. The detection algorithm analyses patterns over a 60-minute window.

While waiting, you can monitor progress:
```bash
# Check all pods are still running
kubectl get pods -n test-scenarios

# Check Prometheus is collecting data
kubectl port-forward -n monitoring svc/prometheus-server 9090:9090 &
```
Open http://localhost:9090 in your browser and query: `container_cpu_usage_seconds_total`

If you see results, Prometheus is collecting metrics. Now wait until 45-60 minutes have passed since Step 8.

---

## Running the Detector

After waiting 45-60 minutes for metrics to accumulate:

**Start the Prometheus port-forward (if not already running):**
```bash
kubectl port-forward -n monitoring svc/prometheus-server 9090:9090 &
```

> **Note:** If you get an error "bind: address already in use", port-forward is already running. Skip this command.

**Run the detector with detailed output:**
```bash
python -m src.main --prometheus-url=http://localhost:9090 --details --exclude-namespaces=kube-system,kube-public,kube-node-lease,monitoring,zombie-detector
```

You should see output like:
```
======================================================================
ZOMBIE CONTAINER DETECTION REPORT
======================================================================

Summary: 7 containers analysed
  Zombies:           4-5
  Potential Zombies: 0-1
  Normal:            2

[ZOMBIE] test-scenarios/.../zombie-memory-leak — Score: 90.0/100
[ZOMBIE] test-scenarios/.../zombie-network-timeout — Score: 79.6/100
[ZOMBIE] test-scenarios/.../zombie-resource-imbalance — Score: 75.0/100
[ZOMBIE] test-scenarios/.../zombie-low-cpu — Score: 65.0/100
[ZOMBIE] test-scenarios/.../zombie-stuck-process — Score: 60.0/100
[NORMAL] test-scenarios/.../normal-batch — Score: 26.8/100
[NORMAL] test-scenarios/.../normal-web — Score: 0.0/100
```

**Get JSON output (for reports):**
```bash
python -m src.main --prometheus-url=http://localhost:9090 --output=json --exclude-namespaces=kube-system,kube-public,kube-node-lease,monitoring,zombie-detector
```

---

## Running the Evaluation

The evaluation script compares the detector's predictions against **ground truth** (we know which containers are zombies because we created them) and calculates accuracy metrics.

```bash
python -m src.evaluation --prometheus-url=http://localhost:9090
```

Expected output:
```
============================================================
EVALUATION RESULTS
============================================================

Accuracy:           100.00%
Precision:          100.00%
Recall:             100.00%
F1 Score:           100.00%
False Positive Rate: 0.00%

Confusion Matrix:
  True Positives:  5
  True Negatives:  2
  False Positives: 0
  False Negatives: 0

Per-Container Results:
Container                      Expected     Predicted             Score  Correct
--------------------------------------------------------------------------------
zombie-memory-leak             zombie       zombie                90.0      YES
zombie-network-timeout         zombie       zombie                79.6      YES
zombie-resource-imbalance      zombie       zombie                75.0      YES
zombie-low-cpu                 zombie       zombie                65.0      YES
zombie-stuck-process           zombie       zombie                60.6      YES
normal-batch                   normal       normal                26.8      YES
normal-web                     normal       normal                 0.0      YES

Target accuracy: 90.0% | Actual: 100.0% | PASS
```

This also saves results to:
- `evaluation_results.csv` — CSV format
- `evaluation_results.json` — JSON format (use `--output-json=evaluation_results.json`)

---

## Viewing the Grafana Dashboard

**Start the Grafana port-forward:**
```bash
kubectl port-forward -n monitoring svc/grafana 3000:3000 &
```

**Open in your browser:**
```
http://localhost:3000
```

**Login:**
- Username: `admin`
- Password: `admin`
- Click "Skip" if it asks you to change the password

**Navigate to the dashboard:**
1. Click the hamburger menu (three lines) on the top left
2. Click **Dashboards**
3. Click the folder **Zombie Detection**
4. Click **Zombie Container Detection Dashboard**

You will see:
- **Top row:** 4 stat panels (total, zombies, potential, normal)
- **Middle:** Zombie scores over time graph with red/orange threshold lines
- **Below:** 5 per-rule charts showing which rules triggered
- **Bottom:** Raw CPU, memory, network charts + classification donut

---

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

---

## Project Structure

```
zombie-container-detection/
├── src/
│   ├── __init__.py            # Python package marker
│   ├── main.py                # CLI entry point
│   ├── detector.py            # Detection orchestrator
│   ├── heuristics.py          # 5 heuristic rules engine (core logic)
│   ├── metrics_collector.py   # Prometheus PromQL queries
│   ├── exporter.py            # Prometheus metrics exporter for Grafana
│   └── evaluation.py          # Accuracy evaluation against ground truth
├── kubernetes/
│   ├── namespaces.yaml        # Namespace definitions (monitoring, test-scenarios, zombie-detector)
│   ├── rbac.yaml              # ServiceAccount & ClusterRole for detector
│   ├── prometheus/
│   │   ├── config.yaml        # Prometheus scrape configuration
│   │   └── deployment.yaml    # Prometheus deployment + service
│   ├── grafana/
│   │   ├── datasource.yaml    # Grafana → Prometheus data source
│   │   ├── dashboard-provider.yaml  # Auto-provisioning config
│   │   ├── dashboard.yaml     # Dashboard JSON (12 panels)
│   │   └── deployment.yaml    # Grafana deployment + service
│   ├── detector/
│   │   └── deployment.yaml    # Detector deployment + service
│   └── test-scenarios/
│       ├── normal-web.yaml           # Active web server (normal)
│       ├── normal-batch.yaml         # Periodic batch processor (normal)
│       ├── zombie-low-cpu.yaml       # Idle with memory held (zombie)
│       ├── zombie-memory-leak.yaml   # Gradual memory growth (zombie)
│       ├── zombie-stuck-process.yaml # Retry loop pattern (zombie)
│       ├── zombie-network-timeout.yaml  # Dead service retries (zombie)
│       └── zombie-resource-imbalance.yaml  # Over-provisioned idle (zombie)
├── Dockerfile                 # Container image for detector
├── requirements.txt           # Python dependencies
├── setup.sh                   # Full AWS EKS setup script (automated)
├── deploy.sh                  # Deploy to existing cluster (automated)
├── cleanup.sh                 # Remove all resources
└── docs/                      # Paper critical reviews
```

---

## Cleanup — Delete Everything When Done

> **IMPORTANT:** EKS clusters cost money (~$0.10/hour for the control plane + EC2 instance costs). **Always delete your cluster when you are done.**

### Remove deployed resources only (keeps the cluster):
```bash
chmod +x cleanup.sh
./cleanup.sh
```

### Delete the EKS cluster completely (recommended when finished):
```bash
# Replace YOUR_NAME with the same name you used during setup
export CLUSTER_NAME=zombie-detector-YOUR_NAME

DELETE_CLUSTER=true CLUSTER_NAME=$CLUSTER_NAME ./cleanup.sh
```

Or manually:
```bash
eksctl delete cluster --name zombie-detector-YOUR_NAME --region us-east-1
```

This takes 5-10 minutes. Wait until it completes.

**Verify cluster is deleted:**
```bash
eksctl get cluster --region us-east-1
```
Your cluster should no longer appear in the list.

---

## Troubleshooting

### "command not found: aws / kubectl / eksctl / docker"
The tool is not installed or not in your PATH. Go back to the [Prerequisites](#prerequisites--install-everything-you-need) section and install it.

### "Unable to locate credentials" or "InvalidClientTokenId"
Your AWS credentials are wrong or expired. Run `aws configure` again with the correct Access Key and Secret Key.

### "error: You must be logged in to the server"
Your kubectl is not connected to the cluster. Run:
```bash
aws eks update-kubeconfig --name zombie-detector-YOUR_NAME --region us-east-1
```

### Port-forward dies / "connection refused"
The port-forward process sometimes stops. Kill it and restart:
```bash
# Kill all port-forwards
pkill -f "port-forward" 2>/dev/null

# Restart the one you need
kubectl port-forward -n monitoring svc/prometheus-server 9090:9090 &
kubectl port-forward -n monitoring svc/grafana 3000:3000 &
```

### "bind: address already in use" when port-forwarding
The port is already in use. Either:
- The port-forward is already running (just use it)
- Kill it first: `pkill -f "port-forward"` then try again

### Detector shows 0 score for all containers
You haven't waited long enough. The detector needs **45-60 minutes** of metric data. Check how long your test pods have been running:
```bash
kubectl get pods -n test-scenarios
```
Look at the `AGE` column. Wait until it shows at least 45 minutes.

### "InvalidImageName" or "ImagePullBackOff" on detector pod
The Docker image was not pushed correctly. Redo Step 9 (build, tag, push, deploy).

### Grafana shows "No data"
1. Make sure Prometheus is running: `kubectl get pods -n monitoring`
2. Make sure the detector is running: `kubectl get pods -n zombie-detector`
3. Wait at least 5-10 minutes after the detector starts for metrics to appear

### EKS cluster creation fails
- Check you have enough AWS permissions (EKS, EC2, CloudFormation, IAM)
- Try a different region if `us-east-1` is full: `--region us-west-2`
- If sharing an account, make sure your cluster name is unique
