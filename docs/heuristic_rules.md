# Heuristic Rules for Zombie Container Detection

This document outlines the heuristic rules used to identify zombie containers in Kubernetes environments.

## Definition of a Zombie Container

A zombie container is defined as a container that:
1. Consumes computational resources (CPU, memory)
2. Does not perform useful work
3. Remains in this state for an extended period

## Heuristic Rules

### Rule 1: Sustained Low CPU with Memory Allocation

**Description:** Containers that maintain very low CPU usage while retaining significant memory allocation over an extended period.

**Parameters:**
- CPU usage < 5% for > 30 minutes
- Memory usage remains constant or increases
- No significant network I/O activity

**Rationale:** Legitimate idle containers typically have periodic spikes in CPU usage or minimal memory allocation. Containers that hold memory without CPU activity are likely zombies.

### Rule 2: Memory Leak Pattern

**Description:** Containers showing a pattern of gradually increasing memory usage with minimal CPU activity.

**Parameters:**
- CPU usage < 3% consistently
- Memory usage increases by > 5% over 1 hour
- No corresponding increase in workload metrics

**Rationale:** This pattern indicates a potential memory leak, where the container is accumulating memory without performing useful work.

### Rule 3: Stuck Process Pattern

**Description:** Containers that show brief CPU spikes followed by extended periods of minimal activity.

**Parameters:**
- CPU usage spikes to > 50% for < 30 seconds
- Followed by CPU usage < 2% for > 15 minutes
- Pattern repeats at least 3 times

**Rationale:** This pattern suggests a process that is stuck in a loop, attempting to perform work but failing and then idling.

### Rule 4: Network Timeout Pattern

**Description:** Containers with minimal CPU and network activity, but periodic network connection attempts.

**Parameters:**
- CPU usage < 5% consistently
- Network connections initiated but < 1KB data transferred
- Connection attempts occur periodically (every 1-5 minutes)

**Rationale:** This pattern indicates a container that may be attempting to connect to unavailable services, becoming effectively useless.

### Rule 5: Resource Ratio Imbalance

**Description:** Containers with an unusual ratio of allocated to used resources.

**Parameters:**
- Memory allocation > 500MB
- Memory usage < 10% of allocated memory
- CPU usage < 1% consistently for > 1 hour

**Rationale:** This pattern indicates over-provisioned containers that are not utilizing their allocated resources effectively.

## Combining Rules

The detection system will use a scoring mechanism that combines these rules:
- Each rule contributes a score from 0-100
- Weights are assigned to each rule based on its reliability
- A combined score > 70 indicates a likely zombie container
- A combined score between 40-70 indicates a potential zombie requiring further investigation

## Exclusion Criteria

Some containers should be excluded from zombie detection:
- System containers (kube-system namespace)
- Recently created containers (< 10 minutes old)
- Containers explicitly labeled with `zombie-detection.exclude=true`
- Batch job containers with known idle periods

## Implementation Notes

The detection system should:
1. Collect metrics at 15-second intervals
2. Analyze patterns over different time windows (5min, 30min, 1hr, 6hr)
3. Apply different rule weights based on container type and workload
4. Provide confidence scores for each detection
