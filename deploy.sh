#!/bin/bash
# =============================================================================
# Deploy all components (assumes cluster already exists and kubectl configured)
# =============================================================================
set -euo pipefail

echo "Deploying Zombie Container Detection System..."

# Namespaces
echo "[1/4] Creating namespaces..."
kubectl apply -f kubernetes/namespaces.yaml

# RBAC
echo "[2/4] Deploying RBAC..."
kubectl apply -f kubernetes/rbac.yaml

# Prometheus
echo "[3/4] Deploying Prometheus..."
kubectl apply -f kubernetes/prometheus/config.yaml
kubectl apply -f kubernetes/prometheus/deployment.yaml
echo "Waiting for Prometheus..."
kubectl wait --for=condition=available --timeout=120s deployment/prometheus-server -n monitoring

# Test scenarios
echo "[4/4] Deploying test scenarios..."
for f in kubernetes/test-scenarios/*.yaml; do
    kubectl apply -f "$f"
done
echo "Waiting for test pods..."
kubectl wait --for=condition=available --timeout=120s deployment --all -n test-scenarios

echo ""
echo "All components deployed. Current pods:"
echo ""
echo "=== Monitoring ==="
kubectl get pods -n monitoring
echo ""
echo "=== Test Scenarios ==="
kubectl get pods -n test-scenarios
echo ""
echo "IMPORTANT: Wait 30-60 minutes for metrics to accumulate before running evaluation."
echo ""
echo "To run detector locally:"
echo "  kubectl port-forward -n monitoring svc/prometheus-server 9090:9090 &"
echo "  python -m src.main --prometheus-url=http://localhost:9090 --details"
echo ""
echo "To run evaluation:"
echo "  python -m src.evaluation --prometheus-url=http://localhost:9090"
