# User Guide

This guide provides instructions for using the Zombie Container Detection tool.

## Installation

Follow these steps to install and set up the tool:

1. **Prerequisites**:
   - Kubernetes cluster (or Minikube for local development)
   - kubectl configured to access your cluster
   - Prometheus and Grafana installed (see [Installation Guide](installation.md))

2. **Deploy the Detector**:
   ```bash
   # Apply the Kubernetes manifests
   kubectl apply -f kubernetes/detector/namespace.yaml
   kubectl apply -f kubernetes/detector/serviceaccount.yaml
   kubectl apply -f kubernetes/detector/configmap.yaml
   kubectl apply -f kubernetes/detector/deployment.yaml
   ```

3. **Verify Deployment**:
   ```bash
   kubectl get pods -n zombie-detector
   ```

## Usage

### Command-Line Interface

The tool provides a command-line interface for detecting zombie containers:

```bash
python src/main.py --prometheus-url=http://prometheus.monitoring:9090 --duration=60 --threshold=70 --output=text
```

#### Options:

- `--prometheus-url`: URL of the Prometheus server
- `--duration`: Duration in minutes to analyze metrics for
- `--threshold`: Score threshold for zombie classification
- `--exclude-namespaces`: Comma-separated list of namespaces to exclude
- `--output`: Output format (json or text)
- `--continuous`: Run in continuous mode with periodic checks
- `--interval`: Interval in seconds between checks in continuous mode
- `--details`: Show detailed analysis for each zombie container

### Continuous Monitoring

To run the tool in continuous monitoring mode:

```bash
python src/main.py --prometheus-url=http://prometheus.monitoring:9090 --continuous --interval=300
```

This will check for zombie containers every 5 minutes and output the results.

### Viewing Results in Grafana

1. Access the Grafana dashboard:
   ```bash
   kubectl port-forward svc/grafana -n monitoring 3000:3000
   ```

2. Open a web browser and navigate to `http://localhost:3000`

3. Log in with the default credentials (admin/admin)

4. Import the zombie container dashboard (available in the `kubernetes/monitoring` directory)

## Configuration

### Excluding Namespaces

To exclude specific namespaces from detection:

```bash
python src/main.py --exclude-namespaces=kube-system,monitoring,default
```

### Excluding Containers with Labels

Containers with the label `zombie-detection.exclude=true` are automatically excluded from detection.

To add this label to a deployment:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-deployment
  labels:
    zombie-detection.exclude: "true"
```

### Adjusting Detection Thresholds

The detection thresholds can be adjusted by modifying the `thresholds` dictionary in the `ZombieHeuristics` class in `src/detector/heuristics.py`.

## Troubleshooting

### Common Issues

1. **No containers detected**:
   - Ensure Prometheus is correctly scraping container metrics
   - Check that the detector has the necessary permissions

2. **False positives**:
   - Adjust the detection threshold (increase for fewer false positives)
   - Exclude namespaces with known idle containers

3. **False negatives**:
   - Adjust the detection threshold (decrease for fewer false negatives)
   - Check that all heuristic rules are working correctly

### Logs

To view the detector logs:

```bash
kubectl logs -f deployment/zombie-detector -n zombie-detector
```

## Evaluation

To evaluate the detector's performance against test scenarios:

1. Deploy the test scenarios:
   ```bash
   kubectl apply -f kubernetes/test-scenarios/
   ```

2. Wait for the containers to run for at least 30 minutes to generate sufficient metrics

3. Run the evaluation script:
   ```bash
   python src/evaluation.py --prometheus-url=http://prometheus.monitoring:9090
   ```

4. Review the evaluation results in the generated CSV file
