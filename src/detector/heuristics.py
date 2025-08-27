"""
Heuristic Rules for Zombie Container Detection

This module implements the heuristic rules for detecting zombie containers
based on resource usage patterns.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ZombieHeuristics:
    """Implements heuristic rules for zombie container detection."""
    
    def __init__(self):
        """Initialize the zombie heuristics detector."""
        # Define rule weights
        self.rule_weights = {
            "sustained_low_cpu": 0.35,
            "memory_leak": 0.25,
            "stuck_process": 0.15,
            "network_timeout": 0.15,
            "resource_imbalance": 0.10
        }
        
        # Define thresholds
        self.thresholds = {
            "low_cpu_percent": 5.0,
            "low_cpu_duration_minutes": 30,
            "memory_increase_percent": 5.0,
            "memory_increase_duration_hours": 1,
            "cpu_spike_percent": 50.0,
            "cpu_spike_duration_seconds": 30,
            "post_spike_low_cpu_percent": 2.0,
            "post_spike_duration_minutes": 15,
            "spike_pattern_count": 3,
            "network_low_transfer_kb": 1.0,
            "network_attempt_interval_minutes": 5,
            "memory_min_allocation_mb": 500,
            "memory_usage_ratio_percent": 10.0,
            "very_low_cpu_percent": 1.0,
            "very_low_cpu_duration_hours": 1
        }
        
        logger.info("Initialized ZombieHeuristics with default thresholds")
    
    def analyze_container(self, metrics: Dict[str, pd.DataFrame], 
                         resource_limits: Dict[str, float]) -> Dict[str, Any]:
        """
        Analyze container metrics using heuristic rules.
        
        Args:
            metrics: Dictionary of DataFrames containing container metrics
            resource_limits: Dictionary containing container resource limits
            
        Returns:
            Dictionary containing analysis results and zombie score
        """
        results = {}
        
        # Apply each heuristic rule
        rule1_score, rule1_details = self._rule_sustained_low_cpu(metrics)
        rule2_score, rule2_details = self._rule_memory_leak(metrics)
        rule3_score, rule3_details = self._rule_stuck_process(metrics)
        rule4_score, rule4_details = self._rule_network_timeout(metrics)
        rule5_score, rule5_details = self._rule_resource_imbalance(metrics, resource_limits)
        
        # Calculate weighted score
        weighted_score = (
            rule1_score * self.rule_weights["sustained_low_cpu"] +
            rule2_score * self.rule_weights["memory_leak"] +
            rule3_score * self.rule_weights["stuck_process"] +
            rule4_score * self.rule_weights["network_timeout"] +
            rule5_score * self.rule_weights["resource_imbalance"]
        ) * 100  # Convert to 0-100 scale
        
        # Determine classification
        classification = "normal"
        if weighted_score >= 70:
            classification = "zombie"
        elif weighted_score >= 40:
            classification = "potential_zombie"
        
        # Compile results
        results = {
            "classification": classification,
            "score": weighted_score,
            "rule_scores": {
                "sustained_low_cpu": rule1_score,
                "memory_leak": rule2_score,
                "stuck_process": rule3_score,
                "network_timeout": rule4_score,
                "resource_imbalance": rule5_score
            },
            "details": {
                "sustained_low_cpu": rule1_details,
                "memory_leak": rule2_details,
                "stuck_process": rule3_details,
                "network_timeout": rule4_details,
                "resource_imbalance": rule5_details
            }
        }
        
        return results
    
    def _rule_sustained_low_cpu(self, metrics: Dict[str, pd.DataFrame]) -> Tuple[float, Dict[str, Any]]:
        """
        Rule 1: Sustained Low CPU with Memory Allocation
        
        Args:
            metrics: Dictionary of DataFrames containing container metrics
            
        Returns:
            Tuple of (score, details)
        """
        cpu_df = metrics.get("cpu", pd.DataFrame())
        memory_df = metrics.get("memory", pd.DataFrame())
        network_rx_df = metrics.get("network_rx", pd.DataFrame())
        network_tx_df = metrics.get("network_tx", pd.DataFrame())
        
        if cpu_df.empty or memory_df.empty:
            return 0.0, {"reason": "Insufficient data"}
        
        # Check if CPU usage is consistently low
        low_cpu_threshold = self.thresholds["low_cpu_percent"] / 100  # Convert to decimal
        low_cpu_samples = cpu_df[cpu_df["value"] < low_cpu_threshold]
        
        if len(low_cpu_samples) == 0:
            return 0.0, {"reason": "CPU usage not consistently low"}
        
        # Calculate the duration of low CPU usage
        if len(low_cpu_samples) < 2:
            return 0.0, {"reason": "Not enough low CPU samples"}
            
        low_cpu_duration = (low_cpu_samples["timestamp"].max() - 
                           low_cpu_samples["timestamp"].min()).total_seconds() / 60
        
        # Check if memory usage remains constant or increases
        if len(memory_df) < 2:
            return 0.0, {"reason": "Not enough memory samples"}
            
        memory_start = memory_df["value"].iloc[0]
        memory_end = memory_df["value"].iloc[-1]
        memory_change_percent = ((memory_end - memory_start) / memory_start) * 100 if memory_start > 0 else 0
        
        # Check network activity
        network_active = False
        if not network_rx_df.empty and not network_tx_df.empty:
            avg_rx = network_rx_df["value"].mean()
            avg_tx = network_tx_df["value"].mean()
            network_active = avg_rx > 1000 or avg_tx > 1000  # More than 1KB/s
        
        # Calculate score based on conditions
        score = 0.0
        details = {}
        
        if low_cpu_duration >= self.thresholds["low_cpu_duration_minutes"]:
            # Base score for sustained low CPU
            score = 0.6
            details["low_cpu_duration_minutes"] = low_cpu_duration
            
            # Adjust score based on memory behavior
            if memory_change_percent >= 0:  # Memory stable or increasing
                score += 0.2
                details["memory_change_percent"] = memory_change_percent
            
            # Adjust score based on network activity
            if not network_active:
                score += 0.2
                details["network_active"] = network_active
        
        return score, details
    
    def _rule_memory_leak(self, metrics: Dict[str, pd.DataFrame]) -> Tuple[float, Dict[str, Any]]:
        """
        Rule 2: Memory Leak Pattern
        
        Args:
            metrics: Dictionary of DataFrames containing container metrics
            
        Returns:
            Tuple of (score, details)
        """
        cpu_df = metrics.get("cpu", pd.DataFrame())
        memory_df = metrics.get("memory", pd.DataFrame())
        
        if cpu_df.empty or memory_df.empty or len(memory_df) < 2:
            return 0.0, {"reason": "Insufficient data"}
        
        # Check if CPU usage is consistently low
        very_low_cpu_threshold = self.thresholds["very_low_cpu_percent"] / 100  # Convert to decimal
        cpu_samples = cpu_df[cpu_df["value"] < very_low_cpu_threshold]
        
        if len(cpu_samples) / len(cpu_df) < 0.9:  # At least 90% of samples below threshold
            return 0.0, {"reason": "CPU usage not consistently very low"}
        
        # Check for memory increase pattern
        memory_start = memory_df["value"].iloc[0]
        memory_end = memory_df["value"].iloc[-1]
        
        if memory_start <= 0:
            return 0.0, {"reason": "Invalid initial memory value"}
        
        memory_increase_percent = ((memory_end - memory_start) / memory_start) * 100
        
        # Calculate duration in hours
        if len(memory_df) < 2:
            return 0.0, {"reason": "Not enough memory samples"}
            
        duration_hours = (memory_df["timestamp"].max() - 
                         memory_df["timestamp"].min()).total_seconds() / 3600
        
        # Calculate score based on conditions
        score = 0.0
        details = {
            "memory_increase_percent": memory_increase_percent,
            "duration_hours": duration_hours
        }
        
        if (memory_increase_percent > self.thresholds["memory_increase_percent"] and 
            duration_hours >= self.thresholds["memory_increase_duration_hours"]):
            # Base score
            score = 0.5
            
            # Adjust score based on severity of memory increase
            if memory_increase_percent > self.thresholds["memory_increase_percent"] * 2:
                score += 0.3
            elif memory_increase_percent > self.thresholds["memory_increase_percent"] * 1.5:
                score += 0.2
            else:
                score += 0.1
            
            # Adjust score based on duration
            if duration_hours >= self.thresholds["memory_increase_duration_hours"] * 2:
                score += 0.2
            else:
                score += 0.1
        
        return score, details
    
    def _rule_stuck_process(self, metrics: Dict[str, pd.DataFrame]) -> Tuple[float, Dict[str, Any]]:
        """
        Rule 3: Stuck Process Pattern
        
        Args:
            metrics: Dictionary of DataFrames containing container metrics
            
        Returns:
            Tuple of (score, details)
        """
        cpu_df = metrics.get("cpu", pd.DataFrame())
        
        if cpu_df.empty or len(cpu_df) < 10:  # Need enough samples to detect pattern
            return 0.0, {"reason": "Insufficient data"}
        
        # Define thresholds
        cpu_spike_threshold = self.thresholds["cpu_spike_percent"] / 100
        post_spike_low_threshold = self.thresholds["post_spike_low_cpu_percent"] / 100
        
        # Find CPU spikes
        cpu_spikes = []
        spike_start_idx = None
        
        for i in range(len(cpu_df)):
            if cpu_df["value"].iloc[i] >= cpu_spike_threshold:
                if spike_start_idx is None:
                    spike_start_idx = i
            elif spike_start_idx is not None:
                spike_end_idx = i - 1
                spike_duration = (cpu_df["timestamp"].iloc[spike_end_idx] - 
                                 cpu_df["timestamp"].iloc[spike_start_idx]).total_seconds()
                
                if spike_duration <= self.thresholds["cpu_spike_duration_seconds"]:
                    cpu_spikes.append({
                        "start_idx": spike_start_idx,
                        "end_idx": spike_end_idx,
                        "duration": spike_duration
                    })
                
                spike_start_idx = None
        
        # Check for post-spike low CPU periods
        pattern_count = 0
        
        for spike in cpu_spikes:
            end_idx = spike["end_idx"]
            if end_idx + 1 >= len(cpu_df):
                continue
                
            # Look for sustained low CPU after spike
            low_period_start = end_idx + 1
            low_period_samples = []
            
            for i in range(low_period_start, len(cpu_df)):
                if cpu_df["value"].iloc[i] < post_spike_low_threshold:
                    low_period_samples.append(i)
                else:
                    break
            
            if len(low_period_samples) < 2:
                continue
                
            low_period_duration = (cpu_df["timestamp"].iloc[low_period_samples[-1]] - 
                                  cpu_df["timestamp"].iloc[low_period_samples[0]]).total_seconds() / 60
            
            if low_period_duration >= self.thresholds["post_spike_duration_minutes"]:
                pattern_count += 1
        
        # Calculate score based on pattern count
        score = 0.0
        details = {"pattern_count": pattern_count}
        
        if pattern_count >= self.thresholds["spike_pattern_count"]:
            score = 0.7 + min(0.3, (pattern_count - self.thresholds["spike_pattern_count"]) * 0.1)
        elif pattern_count > 0:
            score = 0.3 + (pattern_count / self.thresholds["spike_pattern_count"]) * 0.4
        
        return score, details
    
    def _rule_network_timeout(self, metrics: Dict[str, pd.DataFrame]) -> Tuple[float, Dict[str, Any]]:
        """
        Rule 4: Network Timeout Pattern
        
        Args:
            metrics: Dictionary of DataFrames containing container metrics
            
        Returns:
            Tuple of (score, details)
        """
        cpu_df = metrics.get("cpu", pd.DataFrame())
        network_rx_df = metrics.get("network_rx", pd.DataFrame())
        network_tx_df = metrics.get("network_tx", pd.DataFrame())
        
        if cpu_df.empty or network_rx_df.empty or network_tx_df.empty:
            return 0.0, {"reason": "Insufficient data"}
        
        # Check if CPU usage is consistently low
        low_cpu_threshold = self.thresholds["low_cpu_percent"] / 100
        low_cpu_ratio = len(cpu_df[cpu_df["value"] < low_cpu_threshold]) / len(cpu_df)
        
        if low_cpu_ratio < 0.9:  # At least 90% of samples below threshold
            return 0.0, {"reason": "CPU usage not consistently low"}
        
        # Check for periodic network connection attempts with minimal data transfer
        low_transfer_threshold = self.thresholds["network_low_transfer_kb"] * 1024  # Convert to bytes
        
        # Find network activity spikes
        network_spikes = []
        
        for i in range(len(network_tx_df)):
            if network_tx_df["value"].iloc[i] > 0 and network_tx_df["value"].iloc[i] < low_transfer_threshold:
                network_spikes.append({
                    "timestamp": network_tx_df["timestamp"].iloc[i],
                    "tx_value": network_tx_df["value"].iloc[i],
                    "rx_value": network_rx_df["value"].iloc[i] if i < len(network_rx_df) else 0
                })
        
        # Check if there are enough spikes
        if len(network_spikes) < 3:
            return 0.0, {"reason": "Not enough network activity spikes"}
        
        # Check for periodicity in network spikes
        intervals = []
        for i in range(1, len(network_spikes)):
            interval = (network_spikes[i]["timestamp"] - 
                       network_spikes[i-1]["timestamp"]).total_seconds() / 60
            intervals.append(interval)
        
        if not intervals:
            return 0.0, {"reason": "Could not calculate intervals"}
        
        avg_interval = sum(intervals) / len(intervals)
        interval_std = np.std(intervals)
        
        # Calculate coefficient of variation to check periodicity
        cv = interval_std / avg_interval if avg_interval > 0 else float('inf')
        
        # Calculate score based on conditions
        score = 0.0
        details = {
            "network_spike_count": len(network_spikes),
            "avg_interval_minutes": avg_interval,
            "interval_cv": cv
        }
        
        # Check if intervals are within expected range and consistent
        if (1 <= avg_interval <= self.thresholds["network_attempt_interval_minutes"] * 2 and cv < 0.5):
            # Base score
            score = 0.5
            
            # Adjust score based on number of spikes
            if len(network_spikes) >= 10:
                score += 0.3
            elif len(network_spikes) >= 5:
                score += 0.2
            else:
                score += 0.1
            
            # Adjust score based on consistency of intervals
            if cv < 0.3:
                score += 0.2
            elif cv < 0.4:
                score += 0.1
        
        return score, details
    
    def _rule_resource_imbalance(self, metrics: Dict[str, pd.DataFrame], 
                               resource_limits: Dict[str, float]) -> Tuple[float, Dict[str, Any]]:
        """
        Rule 5: Resource Ratio Imbalance
        
        Args:
            metrics: Dictionary of DataFrames containing container metrics
            resource_limits: Dictionary containing container resource limits
            
        Returns:
            Tuple of (score, details)
        """
        cpu_df = metrics.get("cpu", pd.DataFrame())
        memory_df = metrics.get("memory", pd.DataFrame())
        
        if cpu_df.empty or memory_df.empty:
            return 0.0, {"reason": "Insufficient data"}
        
        memory_limit = resource_limits.get("memory_limit", 0)
        
        # Check if memory allocation is significant
        memory_allocation_mb = memory_limit / (1024 * 1024)  # Convert to MB
        
        if memory_allocation_mb < self.thresholds["memory_min_allocation_mb"]:
            return 0.0, {"reason": "Memory allocation below threshold"}
        
        # Calculate average memory usage
        avg_memory_usage = memory_df["value"].mean()
        
        # Calculate memory usage ratio
        memory_usage_ratio = (avg_memory_usage / memory_limit) * 100 if memory_limit > 0 else 0
        
        # Check if CPU usage is consistently very low
        very_low_cpu_threshold = self.thresholds["very_low_cpu_percent"] / 100
        very_low_cpu_samples = cpu_df[cpu_df["value"] < very_low_cpu_threshold]
        
        if len(very_low_cpu_samples) < 2:
            return 0.0, {"reason": "Not enough very low CPU samples"}
            
        very_low_cpu_duration = (very_low_cpu_samples["timestamp"].max() - 
                               very_low_cpu_samples["timestamp"].min()).total_seconds() / 3600
        
        # Calculate score based on conditions
        score = 0.0
        details = {
            "memory_allocation_mb": memory_allocation_mb,
            "memory_usage_ratio": memory_usage_ratio,
            "very_low_cpu_duration_hours": very_low_cpu_duration
        }
        
        if (memory_usage_ratio < self.thresholds["memory_usage_ratio_percent"] and 
            very_low_cpu_duration >= self.thresholds["very_low_cpu_duration_hours"]):
            # Base score
            score = 0.4
            
            # Adjust score based on memory allocation size
            if memory_allocation_mb >= self.thresholds["memory_min_allocation_mb"] * 4:
                score += 0.3
            elif memory_allocation_mb >= self.thresholds["memory_min_allocation_mb"] * 2:
                score += 0.2
            else:
                score += 0.1
            
            # Adjust score based on CPU duration
            if very_low_cpu_duration >= self.thresholds["very_low_cpu_duration_hours"] * 2:
                score += 0.3
            else:
                score += 0.1
        
        return score, details
