# Installation Guide

This guide will walk you through setting up the development environment for the Zombie Container Detection project.

## Prerequisites

1. **Windows, macOS, or Linux** operating system
2. **Docker Desktop** installed and running
3. **Minikube** for local Kubernetes development
4. **kubectl** command-line tool
5. **Python 3.8+** with pip
6. **Go 1.16+** for building the detector

## Step 1: Install Minikube

### Windows
```powershell
# Using Chocolatey
choco install minikube

# Or download the installer from:
# https://minikube.sigs.k8s.io/docs/start/
```

### Start Minikube
```powershell
minikube start --driver=docker --cpus=4 --memory=4096m
```

## Step 2: Install Required Python Packages

```powershell
pip install -r requirements.txt
```

## Step 3: Deploy Prometheus and Grafana

```powershell
kubectl apply -f kubernetes/monitoring/
```

## Step 4: Build and Deploy the Zombie Container Detector

```powershell
# Build the detector
cd src/detector
go build -o zombie-detector

# Deploy to Kubernetes
kubectl apply -f kubernetes/detector/
```

## Step 5: Access the Dashboard

```powershell
# Get the URL for Grafana
minikube service grafana -n monitoring --url
```

## Troubleshooting

If you encounter issues with Minikube, try:

```powershell
minikube delete
minikube start --driver=docker
```

For more detailed troubleshooting, see the [Minikube documentation](https://minikube.sigs.k8s.io/docs/handbook/troubleshooting/).
