"""
Metrics Collector for Zombie Container Detection

This module collects container metrics from Prometheus and processes them for analysis.
"""

import time
import logging
from typing import Dict, List, Any, Optional
import requests
import numpy as np
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MetricsCollector:
    """Collects and processes container metrics from Prometheus."""
    
    def __init__(self, prometheus_url: str = "http://prometheus.monitoring:9090"):
        """
        Initialize the metrics collector.
        
        Args:
            prometheus_url: URL of the Prometheus server
        """
        self.prometheus_url = prometheus_url
        self.api_url = f"{prometheus_url}/api/v1"
        logger.info(f"Initialized MetricsCollector with Prometheus URL: {prometheus_url}")
    
    def query(self, query: str) -> Dict[str, Any]:
        """
        Execute a PromQL query against Prometheus.
        
        Args:
            query: PromQL query string
            
        Returns:
            Dict containing the query results
        """
        try:
            response = requests.get(
                f"{self.api_url}/query",
                params={"query": query}
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error querying Prometheus: {e}")
            return {"status": "error", "data": {"result": []}}
    
    def query_range(self, query: str, start: int, end: int, step: str = "15s") -> Dict[str, Any]:
        """
        Execute a PromQL range query against Prometheus.
        
        Args:
            query: PromQL query string
            start: Start timestamp in seconds
            end: End timestamp in seconds
            step: Query resolution step width
            
        Returns:
            Dict containing the query results
        """
        try:
            response = requests.get(
                f"{self.api_url}/query_range",
                params={
                    "query": query,
                    "start": start,
                    "end": end,
                    "step": step
                }
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error querying Prometheus range: {e}")
            return {"status": "error", "data": {"result": []}}
    
    def get_container_list(self) -> List[Dict[str, str]]:
        """
        Get a list of all containers in the cluster.
        
        Returns:
            List of dictionaries containing container metadata
        """
        query = 'container_cpu_usage_seconds_total{container!=""}'
        result = self.query(query)
        
        containers = []
        if result["status"] == "success":
            for metric in result["data"]["result"]:
                container = {
                    "namespace": metric["metric"].get("namespace", ""),
                    "pod": metric["metric"].get("pod", ""),
                    "container": metric["metric"].get("container", ""),
                    "node": metric["metric"].get("node", "")
                }
                containers.append(container)
        
        return containers
    
    def get_container_metrics(self, namespace: str, pod: str, container: str, 
                             duration_minutes: int = 60) -> Dict[str, pd.DataFrame]:
        """
        Get metrics for a specific container over a time period.
        
        Args:
            namespace: Kubernetes namespace
            pod: Pod name
            container: Container name
            duration_minutes: Duration to look back in minutes
            
        Returns:
            Dictionary of DataFrames containing metrics
        """
        end_time = int(time.time())
        start_time = end_time - (duration_minutes * 60)
        step = "15s"
        
        # Query CPU usage rate
        cpu_query = f'rate(container_cpu_usage_seconds_total{{namespace="{namespace}", pod="{pod}", container="{container}"}}[5m])'
        cpu_result = self.query_range(cpu_query, start_time, end_time, step)
        
        # Query memory usage
        memory_query = f'container_memory_usage_bytes{{namespace="{namespace}", pod="{pod}", container="{container}"}}'
        memory_result = self.query_range(memory_query, start_time, end_time, step)
        
        # Query network receive bytes
        network_rx_query = f'rate(container_network_receive_bytes_total{{namespace="{namespace}", pod="{pod}"}}[5m])'
        network_rx_result = self.query_range(network_rx_query, start_time, end_time, step)
        
        # Query network transmit bytes
        network_tx_query = f'rate(container_network_transmit_bytes_total{{namespace="{namespace}", pod="{pod}"}}[5m])'
        network_tx_result = self.query_range(network_tx_query, start_time, end_time, step)
        
        # Process results into DataFrames
        metrics = {
            "cpu": self._process_metric_data(cpu_result),
            "memory": self._process_metric_data(memory_result),
            "network_rx": self._process_metric_data(network_rx_result),
            "network_tx": self._process_metric_data(network_tx_result)
        }
        
        return metrics
    
    def _process_metric_data(self, result: Dict[str, Any]) -> pd.DataFrame:
        """
        Process metric data from Prometheus into a pandas DataFrame.
        
        Args:
            result: Prometheus query result
            
        Returns:
            DataFrame containing the processed metrics
        """
        if result["status"] != "success" or not result["data"]["result"]:
            return pd.DataFrame(columns=["timestamp", "value"])
        
        # Extract the first result (should be only one for specific container)
        data_points = result["data"]["result"][0]["values"]
        
        # Convert to DataFrame
        df = pd.DataFrame(data_points, columns=["timestamp", "value"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
        df["value"] = df["value"].astype(float)
        
        return df
    
    def get_container_resource_limits(self, namespace: str, pod: str, container: str) -> Dict[str, float]:
        """
        Get the resource limits for a container.
        
        Args:
            namespace: Kubernetes namespace
            pod: Pod name
            container: Container name
            
        Returns:
            Dictionary containing CPU and memory limits
        """
        # Query CPU limit
        cpu_limit_query = f'container_spec_cpu_quota{{namespace="{namespace}", pod="{pod}", container="{container}"}}'
        cpu_limit_result = self.query(cpu_limit_query)
        
        # Query memory limit
        memory_limit_query = f'container_spec_memory_limit_bytes{{namespace="{namespace}", pod="{pod}", container="{container}"}}'
        memory_limit_result = self.query(memory_limit_query)
        
        cpu_limit = 0.0
        memory_limit = 0.0
        
        if cpu_limit_result["status"] == "success" and cpu_limit_result["data"]["result"]:
            # CPU quota is in microseconds, divide by 100000 to get cores
            cpu_limit = float(cpu_limit_result["data"]["result"][0]["value"][1]) / 100000
        
        if memory_limit_result["status"] == "success" and memory_limit_result["data"]["result"]:
            memory_limit = float(memory_limit_result["data"]["result"][0]["value"][1])
        
        return {
            "cpu_limit": cpu_limit,
            "memory_limit": memory_limit
        }
