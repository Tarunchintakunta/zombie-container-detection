# Implementation Details

This document provides detailed information about the implementation of the Zombie Container Detection tool.

## Architecture

The Zombie Container Detection tool consists of the following components:

1. **Metrics Collector**: Collects container metrics from Prometheus
2. **Heuristics Engine**: Analyzes metrics using rule-based heuristics
3. **Detector**: Integrates with Kubernetes API and applies heuristics to containers
4. **CLI Interface**: Provides a command-line interface for running the detector

### Component Diagram

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│   Kubernetes    │◄────┤    Detector     │◄────┤  CLI Interface  │
│      API        │     │                 │     │                 │
│                 │     │                 │     │                 │
└────────┬────────┘     └────────┬────────┘     └─────────────────┘
         │                       │
         │                       │
         │               ┌───────▼───────┐     ┌─────────────────┐
         │               │               │     │                 │
         └───────────────►   Heuristics  │◄────┤    Metrics      │
                         │    Engine     │     │   Collector     │
                         │               │     │                 │
                         └───────────────┘     └────────┬────────┘
                                                        │
                                                        │
                                               ┌────────▼────────┐
                                               │                 │
                                               │   Prometheus    │
                                               │                 │
                                               └─────────────────┘
```

## Heuristic Rules

The detection system uses five primary heuristic rules to identify zombie containers:

1. **Sustained Low CPU with Memory Allocation**: Containers with consistently low CPU usage while maintaining significant memory allocation.
2. **Memory Leak Pattern**: Containers showing gradually increasing memory usage with minimal CPU activity.
3. **Stuck Process Pattern**: Containers with brief CPU spikes followed by extended periods of minimal activity.
4. **Network Timeout Pattern**: Containers with minimal CPU and network activity, but periodic network connection attempts.
5. **Resource Ratio Imbalance**: Containers with an unusual ratio of allocated to used resources.

Each rule produces a score between 0 and 1, which is then weighted and combined to produce an overall zombie score between 0 and 100.

## Scoring System

The scoring system works as follows:

1. Each heuristic rule produces a score between 0 and 1
2. Rules are weighted based on their reliability:
   - Sustained Low CPU: 35%
   - Memory Leak: 25%
   - Stuck Process: 15%
   - Network Timeout: 15%
   - Resource Imbalance: 10%
3. The weighted scores are summed and multiplied by 100 to get a final score between 0 and 100
4. Containers with a score ≥ 70 are classified as zombies
5. Containers with a score between 40 and 70 are classified as potential zombies

## Deployment Architecture

The tool is deployed as a Kubernetes deployment in its own namespace, with the following components:

1. **ServiceAccount**: Provides necessary permissions to access pod and node information
2. **ConfigMap**: Contains the application code and configuration
3. **Deployment**: Runs the detector in continuous mode

The detector periodically scans all containers in the cluster, excluding those in specified namespaces or with specific labels.

## Integration with Monitoring Stack

The tool integrates with Prometheus and Grafana for metrics collection and visualization:

1. **Prometheus**: Collects container metrics (CPU, memory, network)
2. **Grafana**: Visualizes metrics and detection results

Custom dashboards can be created in Grafana to monitor zombie containers and their resource usage patterns.
