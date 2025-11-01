"""
Plugin System for Enhanced Tools and Integrations

Provides a plugin architecture for adding new tools and integrations to the collaborative worker system.
Supports plugin discovery, registration, lifecycle management, and capability advertisement.
"""

import logging
import importlib
import inspect
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Type, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from .exceptions import WorkerError


class PluginStatus(Enum):
    """Plugin status enumeration"""
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    ACTIVE = "active"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class PluginCapability:
    """Represents a capability provided by a plugin"""
    name: str
    description: str
    input_types: List[str]
    output_types: List[str]
    requirements: Dict[str, Any]
    collaborative_aware: bool = False


@dataclass
class PluginMetadata:
    """Plugin metadata information"""
    name: str
    version: str
    description: str
    author: str
    capabilities: List[PluginCapability]
    dependencies: List[str]
    collaborative_features: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class IPlugin(ABC):
    """Interface that all plugins must implement"""
    
    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """Get plugin metadata"""
        pass
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the plugin with configuration"""
        pass
    
    @abstractmethod
    def execute(self, capability: str, parameters: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a plugin capability"""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[PluginCapability]:
        """Get list of capabilities provided by this plugin"""
        pass
    
    @abstractmethod
    def shutdown(self) -> None:
        """Shutdown the plugin and cleanup resources"""
        pass
    
    def supports_collaboration(self) -> bool:
        """Check if plugin supports collaborative features"""
        return False
    
    def get_collaborative_features(self) -> Dict[str, Any]:
        """Get collaborative features supported by this plugin"""
        return {}


class PluginRegistry:
    """Registry for managing plugins and their capabilities"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._plugins: Dict[str, IPlugin] = {}
        self._plugin_status: Dict[str, PluginStatus] = {}
        self._plugin_metadata: Dict[str, PluginMetadata] = {}
        self._capability_map: Dict[str, str] = {}  # capability_name -> plugin_name
        self._collaborative_plugins: Dict[str, IPlugin] = {}
        
    def register_plugin(self, plugin: IPlugin) -> bool:
        """
        Register a plugin in the registry
        
        Args:
            plugin: Plugin instance to register
            
        Returns:
            bool: True if registration successful
        """
        try:
            metadata = plugin.get_metadata()
            plugin_name = metadata.name
            
            self.logger.info(f"Registering plugin: {plugin_name}")
            
            # Check for name conflicts
            if plugin_name in self._plugins:
                self.logger.warning(f"Plugin {plugin_name} already registered, replacing")
            
            # Store plugin and metadata
            self._plugins[plugin_name] = plugin
            self._plugin_metadata[plugin_name] = metadata
            self._plugin_status[plugin_name] = PluginStatus.LOADED
            
            # Register capabilities
            for capability in metadata.capabilities:
                if capability.name in self._capability_map:
                    existing_plugin = self._capability_map[capability.name]
                    self.logger.warning(f"Capability {capability.name} already provided by {existing_plugin}, overriding")
                
                self._capability_map[capability.name] = plugin_name
            
            # Track collaborative plugins
            if plugin.supports_collaboration():
                self._collaborative_plugins[plugin_name] = plugin
            
            self.logger.info(f"Plugin {plugin_name} registered successfully with {len(metadata.capabilities)} capabilities")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register plugin: {str(e)}")
            if hasattr(plugin, 'get_metadata'):
                try:
                    plugin_name = plugin.get_metadata().name
                    self._plugin_status[plugin_name] = PluginStatus.ERROR
                except:
                    pass
            return False
    
    def unregister_plugin(self, plugin_name: str) -> bool:
        """
        Unregister a plugin from the registry
        
        Args:
            plugin_name: Name of plugin to unregister
            
        Returns:
            bool: True if unregistration successful
        """
        try:
            if plugin_name not in self._plugins:
                self.logger.warning(f"Plugin {plugin_name} not found for unregistration")
                return False
            
            self.logger.info(f"Unregistering plugin: {plugin_name}")
            
            plugin = self._plugins[plugin_name]
            
            # Shutdown plugin
            try:
                plugin.shutdown()
            except Exception as e:
                self.logger.warning(f"Error shutting down plugin {plugin_name}: {str(e)}")
            
            # Remove capabilities
            capabilities_to_remove = []
            for capability_name, provider_plugin in self._capability_map.items():
                if provider_plugin == plugin_name:
                    capabilities_to_remove.append(capability_name)
            
            for capability_name in capabilities_to_remove:
                del self._capability_map[capability_name]
            
            # Remove from registries
            del self._plugins[plugin_name]
            del self._plugin_metadata[plugin_name]
            del self._plugin_status[plugin_name]
            
            if plugin_name in self._collaborative_plugins:
                del self._collaborative_plugins[plugin_name]
            
            self.logger.info(f"Plugin {plugin_name} unregistered successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to unregister plugin {plugin_name}: {str(e)}")
            return False
    
    def get_plugin(self, plugin_name: str) -> Optional[IPlugin]:
        """Get plugin instance by name"""
        return self._plugins.get(plugin_name)
    
    def get_plugin_by_capability(self, capability_name: str) -> Optional[IPlugin]:
        """Get plugin that provides a specific capability"""
        plugin_name = self._capability_map.get(capability_name)
        if plugin_name:
            return self._plugins.get(plugin_name)
        return None
    
    def list_plugins(self) -> List[str]:
        """Get list of all registered plugin names"""
        return list(self._plugins.keys())
    
    def list_capabilities(self) -> List[str]:
        """Get list of all available capabilities"""
        return list(self._capability_map.keys())
    
    def get_plugin_metadata(self, plugin_name: str) -> Optional[PluginMetadata]:
        """Get metadata for a specific plugin"""
        return self._plugin_metadata.get(plugin_name)
    
    def get_plugin_status(self, plugin_name: str) -> Optional[PluginStatus]:
        """Get status of a specific plugin"""
        return self._plugin_status.get(plugin_name)
    
    def get_collaborative_plugins(self) -> Dict[str, IPlugin]:
        """Get all plugins that support collaborative features"""
        return self._collaborative_plugins.copy()
    
    def find_plugins_by_capability_type(self, capability_type: str) -> List[str]:
        """Find plugins that provide capabilities of a specific type"""
        matching_plugins = []
        
        for plugin_name, metadata in self._plugin_metadata.items():
            for capability in metadata.capabilities:
                if capability_type in capability.input_types or capability_type in capability.output_types:
                    if plugin_name not in matching_plugins:
                        matching_plugins.append(plugin_name)
        
        return matching_plugins


class PluginManager:
    """Manager for plugin lifecycle and execution"""
    
    def __init__(self, registry: PluginRegistry):
        self.logger = logging.getLogger(__name__)
        self.registry = registry
        self._plugin_configs: Dict[str, Dict[str, Any]] = {}
        self._usage_stats: Dict[str, Dict[str, Any]] = {}
        
    def initialize_plugin(self, plugin_name: str, config: Dict[str, Any] = None) -> bool:
        """
        Initialize a plugin with configuration
        
        Args:
            plugin_name: Name of plugin to initialize
            config: Configuration parameters
            
        Returns:
            bool: True if initialization successful
        """
        try:
            plugin = self.registry.get_plugin(plugin_name)
            if not plugin:
                self.logger.error(f"Plugin {plugin_name} not found")
                return False
            
            self.logger.info(f"Initializing plugin: {plugin_name}")
            
            # Store configuration
            self._plugin_configs[plugin_name] = config or {}
            
            # Initialize plugin
            success = plugin.initialize(config or {})
            
            if success:
                self.registry._plugin_status[plugin_name] = PluginStatus.ACTIVE
                self.logger.info(f"Plugin {plugin_name} initialized successfully")
            else:
                self.registry._plugin_status[plugin_name] = PluginStatus.ERROR
                self.logger.error(f"Plugin {plugin_name} initialization failed")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to initialize plugin {plugin_name}: {str(e)}")
            self.registry._plugin_status[plugin_name] = PluginStatus.ERROR
            return False
    
    def execute_capability(self, capability_name: str, parameters: Dict[str, Any], 
                          context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute a capability provided by a plugin
        
        Args:
            capability_name: Name of capability to execute
            parameters: Parameters for the capability
            context: Execution context
            
        Returns:
            Dict containing execution results
        """
        try:
            plugin = self.registry.get_plugin_by_capability(capability_name)
            if not plugin:
                raise WorkerError(
                    f"No plugin found for capability: {capability_name}",
                    context={'operation': 'plugin_execution'}
                )
            
            plugin_name = plugin.get_metadata().name
            
            # Check plugin status
            status = self.registry.get_plugin_status(plugin_name)
            if status != PluginStatus.ACTIVE:
                raise WorkerError(
                    f"Plugin {plugin_name} is not active (status: {status})",
                    context={'operation': 'plugin_execution'}
                )
            
            self.logger.info(f"Executing capability {capability_name} via plugin {plugin_name}")
            
            # Track usage
            self._track_usage(plugin_name, capability_name)
            
            # Execute capability
            result = plugin.execute(capability_name, parameters, context or {})
            
            # Add execution metadata
            result['_plugin_metadata'] = {
                'plugin_name': plugin_name,
                'capability_name': capability_name,
                'executed_at': datetime.now().isoformat(),
                'collaborative_aware': plugin.supports_collaboration()
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to execute capability {capability_name}: {str(e)}")
            raise WorkerError(
                f"Plugin capability execution failed: {str(e)}",
                context={'operation': 'plugin_execution'},
                original_exception=e
            )
    
    def get_capability_info(self, capability_name: str) -> Optional[PluginCapability]:
        """Get information about a specific capability"""
        plugin = self.registry.get_plugin_by_capability(capability_name)
        if not plugin:
            return None
        
        capabilities = plugin.get_capabilities()
        for capability in capabilities:
            if capability.name == capability_name:
                return capability
        
        return None
    
    def list_available_capabilities(self, collaborative_only: bool = False) -> List[PluginCapability]:
        """
        List all available capabilities
        
        Args:
            collaborative_only: If True, only return collaborative-aware capabilities
            
        Returns:
            List of available capabilities
        """
        capabilities = []
        
        plugins_to_check = (
            self.registry.get_collaborative_plugins().values() if collaborative_only 
            else self.registry._plugins.values()
        )
        
        for plugin in plugins_to_check:
            try:
                plugin_capabilities = plugin.get_capabilities()
                if collaborative_only:
                    # Filter for collaborative capabilities
                    plugin_capabilities = [cap for cap in plugin_capabilities if cap.collaborative_aware]
                
                capabilities.extend(plugin_capabilities)
            except Exception as e:
                self.logger.warning(f"Failed to get capabilities from plugin: {str(e)}")
        
        return capabilities
    
    def get_usage_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Get plugin usage statistics"""
        return self._usage_stats.copy()
    
    def _track_usage(self, plugin_name: str, capability_name: str) -> None:
        """Track plugin usage for optimization"""
        try:
            if plugin_name not in self._usage_stats:
                self._usage_stats[plugin_name] = {
                    'total_executions': 0,
                    'capabilities_used': {},
                    'first_used': datetime.now().isoformat(),
                    'last_used': datetime.now().isoformat()
                }
            
            stats = self._usage_stats[plugin_name]
            stats['total_executions'] += 1
            stats['last_used'] = datetime.now().isoformat()
            
            if capability_name not in stats['capabilities_used']:
                stats['capabilities_used'][capability_name] = 0
            stats['capabilities_used'][capability_name] += 1
            
        except Exception as e:
            self.logger.warning(f"Failed to track usage for {plugin_name}: {str(e)}")


class PluginDiscovery:
    """Plugin discovery system for finding and loading plugins"""
    
    def __init__(self, registry: PluginRegistry):
        self.logger = logging.getLogger(__name__)
        self.registry = registry
        self._discovery_paths: List[str] = []
    
    def add_discovery_path(self, path: str) -> None:
        """Add a path for plugin discovery"""
        if path not in self._discovery_paths:
            self._discovery_paths.append(path)
            self.logger.info(f"Added plugin discovery path: {path}")
    
    def discover_plugins(self) -> List[str]:
        """
        Discover available plugins in configured paths
        
        Returns:
            List of discovered plugin names
        """
        discovered_plugins = []
        
        for path in self._discovery_paths:
            try:
                plugins_in_path = self._scan_path_for_plugins(path)
                discovered_plugins.extend(plugins_in_path)
            except Exception as e:
                self.logger.warning(f"Failed to scan path {path} for plugins: {str(e)}")
        
        self.logger.info(f"Discovered {len(discovered_plugins)} plugins")
        return discovered_plugins
    
    def load_plugin_from_module(self, module_name: str, class_name: str = None) -> Optional[IPlugin]:
        """
        Load a plugin from a Python module
        
        Args:
            module_name: Name of the module to load
            class_name: Specific class name (if None, will search for IPlugin implementations)
            
        Returns:
            Plugin instance if successful
        """
        try:
            self.logger.info(f"Loading plugin from module: {module_name}")
            
            # Import the module
            module = importlib.import_module(module_name)
            
            # Find plugin class
            plugin_class = None
            if class_name:
                plugin_class = getattr(module, class_name, None)
            else:
                # Search for IPlugin implementations
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, IPlugin) and obj != IPlugin:
                        plugin_class = obj
                        break
            
            if not plugin_class:
                self.logger.error(f"No plugin class found in module {module_name}")
                return None
            
            # Instantiate plugin
            plugin_instance = plugin_class()
            
            # Validate plugin
            if not isinstance(plugin_instance, IPlugin):
                self.logger.error(f"Plugin class {plugin_class.__name__} does not implement IPlugin")
                return None
            
            self.logger.info(f"Successfully loaded plugin: {plugin_instance.get_metadata().name}")
            return plugin_instance
            
        except Exception as e:
            self.logger.error(f"Failed to load plugin from module {module_name}: {str(e)}")
            return None
    
    def auto_register_discovered_plugins(self) -> int:
        """
        Automatically discover and register all available plugins
        
        Returns:
            Number of plugins successfully registered
        """
        discovered_plugins = self.discover_plugins()
        registered_count = 0
        
        for plugin_module in discovered_plugins:
            try:
                plugin = self.load_plugin_from_module(plugin_module)
                if plugin and self.registry.register_plugin(plugin):
                    registered_count += 1
            except Exception as e:
                self.logger.warning(f"Failed to auto-register plugin {plugin_module}: {str(e)}")
        
        self.logger.info(f"Auto-registered {registered_count} plugins")
        return registered_count
    
    def _scan_path_for_plugins(self, path: str) -> List[str]:
        """Scan a specific path for plugin modules"""
        # This is a simplified implementation
        # In a real system, this would scan filesystem paths for plugin files
        plugins = []
        
        # For now, return empty list as we'll implement specific plugins later
        return plugins


# Global plugin system instances
_plugin_registry = None
_plugin_manager = None
_plugin_discovery = None


def get_plugin_registry() -> PluginRegistry:
    """Get the global plugin registry instance"""
    global _plugin_registry
    if _plugin_registry is None:
        _plugin_registry = PluginRegistry()
    return _plugin_registry


def get_plugin_manager() -> PluginManager:
    """Get the global plugin manager instance"""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager(get_plugin_registry())
    return _plugin_manager


def get_plugin_discovery() -> PluginDiscovery:
    """Get the global plugin discovery instance"""
    global _plugin_discovery
    if _plugin_discovery is None:
        _plugin_discovery = PluginDiscovery(get_plugin_registry())
    return _plugin_discovery