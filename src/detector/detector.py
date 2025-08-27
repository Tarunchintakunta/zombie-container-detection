"""
Zombie Container Detector

This module implements the main detector for identifying zombie containers
in Kubernetes clusters using heuristic rules.
"""

import logging
import time
from typing import Dict, List, Any, Optional
import pandas as pd
from kubernetes import client, config
from ..metrics.collector import MetricsCollector
from .heuristics import ZombieHeuristics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ZombieDetector:
    """Detects zombie containers in Kubernetes clusters."""
    
    def __init__(self, prometheus_url: str = "http://prometheus.monitoring:9090",
                namespace_exclude: List[str] = None,
                label_exclude: Dict[str, str] = None):
        """
        Initialize the zombie detector.
        
        Args:
            prometheus_url: URL of the Prometheus server
            namespace_exclude: List of namespaces to exclude from detection
            label_exclude: Dictionary of labels to exclude from detection
        """
        self.metrics_collector = MetricsCollector(prometheus_url)
        self.heuristics = ZombieHeuristics()
        
        # Default exclusions
        if namespace_exclude is None:
            namespace_exclude = ["kube-system", "monitoring"]
        
        if label_exclude is None:
            label_exclude = {"zombie-detection.exclude": "true"}
        
        self.namespace_exclude = namespace_exclude
        self.label_exclude = label_exclude
        
        # Initialize Kubernetes client
        try:
            config.load_incluster_config()
            logger.info("Loaded in-cluster Kubernetes configuration")
        except config.ConfigException:
            try:
                config.load_kube_config()
                logger.info("Loaded local Kubernetes configuration")
            except config.ConfigException:
                logger.error("Could not load Kubernetes configuration")
                raise
        
        self.k8s_api = client.CoreV1Api()
        logger.info("Initialized ZombieDetector")
    
    def detect_zombies(self, duration_minutes: int = 60, 
                      score_threshold: float = 70.0) -> List[Dict[str, Any]]:
        """
        Detect zombie containers in the cluster.
        
        Args:
            duration_minutes: Duration to analyze metrics for
            score_threshold: Score threshold for zombie classification
            
        Returns:
            List of dictionaries containing zombie container details
        """
        # Get list of all containers
        containers = self._get_containers()
        logger.info(f"Found {len(containers)} containers to analyze")
        
        zombies = []
        
        # Analyze each container
        for container in containers:
            namespace = container["namespace"]
            pod = container["pod"]
            container_name = container["container"]
            
            # Skip excluded namespaces
            if namespace in self.namespace_exclude:
                logger.debug(f"Skipping container in excluded namespace: {namespace}/{pod}/{container_name}")
                continue
            
            # Skip recently created containers (< 10 minutes old)
            if self._is_recently_created(namespace, pod):
                logger.debug(f"Skipping recently created container: {namespace}/{pod}/{container_name}")
                continue
            
            # Get container metrics
            metrics = self.metrics_collector.get_container_metrics(
                namespace, pod, container_name, duration_minutes
            )
            
            # Get resource limits
            resource_limits = self.metrics_collector.get_container_resource_limits(
                namespace, pod, container_name
            )
            
            # Analyze container using heuristics
            result = self.heuristics.analyze_container(metrics, resource_limits)
            
            # Add container details to result
            result["container"] = {
                "namespace": namespace,
                "pod": pod,
                "container": container_name,
                "node": container.get("node", "")
            }
            
            # Check if container is classified as a zombie
            if result["score"] >= score_threshold:
                zombies.append(result)
                logger.info(f"Detected zombie container: {namespace}/{pod}/{container_name} with score {result['score']:.2f}")
            elif result["score"] >= 40:
                logger.info(f"Potential zombie container: {namespace}/{pod}/{container_name} with score {result['score']:.2f}")
        
        return zombies
    
    def _get_containers(self) -> List[Dict[str, str]]:
        """
        Get list of all containers in the cluster.
        
        Returns:
            List of dictionaries containing container metadata
        """
        containers = []
        
        try:
            # Get all pods in all namespaces
            pods = self.k8s_api.list_pod_for_all_namespaces(watch=False)
            
            for pod in pods.items:
                namespace = pod.metadata.namespace
                pod_name = pod.metadata.name
                node_name = pod.spec.node_name
                
                # Skip pods with exclude labels
                if pod.metadata.labels:
                    skip = False
                    for key, value in self.label_exclude.items():
                        if pod.metadata.labels.get(key) == value:
                            skip = True
                            break
                    if skip:
                        continue
                
                # Add each container in the pod
                for container in pod.spec.containers:
                    containers.append({
                        "namespace": namespace,
                        "pod": pod_name,
                        "container": container.name,
                        "node": node_name
                    })
        except Exception as e:
            logger.error(f"Error getting containers: {e}")
        
        return containers
    
    def _is_recently_created(self, namespace: str, pod_name: str) -> bool:
        """
        Check if a pod was recently created (< 10 minutes ago).
        
        Args:
            namespace: Kubernetes namespace
            pod_name: Pod name
            
        Returns:
            True if pod was recently created, False otherwise
        """
        try:
            pod = self.k8s_api.read_namespaced_pod(pod_name, namespace)
            if pod.status.start_time:
                age_seconds = (time.time() - pod.status.start_time.timestamp())
                return age_seconds < 600  # 10 minutes
        except Exception as e:
            logger.error(f"Error checking pod age: {e}")
        
        return False
    
    def get_zombie_details(self, namespace: str, pod_name: str, 
                         container_name: str) -> Dict[str, Any]:
        """
        Get detailed analysis for a specific container.
        
        Args:
            namespace: Kubernetes namespace
            pod_name: Pod name
            container_name: Container name
            
        Returns:
            Dictionary containing detailed analysis
        """
        # Get container metrics for a longer duration
        metrics = self.metrics_collector.get_container_metrics(
            namespace, pod_name, container_name, duration_minutes=120
        )
        
        # Get resource limits
        resource_limits = self.metrics_collector.get_container_resource_limits(
            namespace, pod_name, container_name
        )
        
        # Analyze container using heuristics
        result = self.heuristics.analyze_container(metrics, resource_limits)
        
        # Add container details to result
        result["container"] = {
            "namespace": namespace,
            "pod": pod_name,
            "container": container_name
        }
        
        # Get additional pod details
        try:
            pod = self.k8s_api.read_namespaced_pod(pod_name, namespace)
            result["pod_details"] = {
                "node": pod.spec.node_name,
                "start_time": pod.status.start_time.isoformat() if pod.status.start_time else None,
                "phase": pod.status.phase,
                "qos_class": pod.status.qos_class
            }
        except Exception as e:
            logger.error(f"Error getting pod details: {e}")
        
        return result
