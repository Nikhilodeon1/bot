"""
System Startup Module for Botted Library v2

Provides unified system startup procedures and dependency resolution.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from .system_integration import SystemIntegration, SystemConfiguration, get_system_integration
from .interfaces import WorkerType


@dataclass
class StartupOptions:
    """Options for system startup"""
    config_file: Optional[str] = None
    environment: str = "development"
    auto_start_server: bool = True
    load_plugins: bool = True
    enable_monitoring: bool = True
    enable_error_recovery: bool = True
    log_level: str = "INFO"
    background_mode: bool = False


class SystemStartup:
    """
    Handles system startup procedures and configuration loading
    """
    
    def __init__(self, options: Optional[StartupOptions] = None):
        self.options = options or StartupOptions()
        self.logger = self._setup_logging()
        self.config: Optional[SystemConfiguration] = None
        self.system: Optional[SystemIntegration] = None
    
    def _setup_logging(self) -> logging.Logger:
        """Setup startup logging"""
        logger = logging.getLogger("botted_library.startup")
        logger.setLevel(getattr(logging, self.options.log_level.upper()))
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def load_configuration(self) -> SystemConfiguration:
        """
        Load system configuration from various sources
        """
        self.logger.info("Loading system configuration...")
        
        # Start with default configuration
        config = SystemConfiguration()
        
        # Load from environment variables
        config = self._load_from_environment(config)
        
        # Load from configuration file if specified
        if self.options.config_file:
            config = self._load_from_file(config, self.options.config_file)
        
        # Apply startup options overrides
        config = self._apply_startup_options(config)
        
        self.config = config
        self.logger.info("Configuration loaded successfully")
        return config
    
    def _load_from_environment(self, config: SystemConfiguration) -> SystemConfiguration:
        """Load configuration from environment variables"""
        # Server configuration
        if os.getenv("BOTTED_SERVER_HOST"):
            config.server_host = os.getenv("BOTTED_SERVER_HOST")
        
        if os.getenv("BOTTED_SERVER_PORT"):
            config.server_port = int(os.getenv("BOTTED_SERVER_PORT"))
        
        if os.getenv("BOTTED_MAX_CONNECTIONS"):
            config.server_max_connections = int(os.getenv("BOTTED_MAX_CONNECTIONS"))
        
        # Worker configuration
        if os.getenv("BOTTED_MAX_PLANNERS"):
            config.max_workers_per_type[WorkerType.PLANNER] = int(os.getenv("BOTTED_MAX_PLANNERS"))
        
        if os.getenv("BOTTED_MAX_EXECUTORS"):
            config.max_workers_per_type[WorkerType.EXECUTOR] = int(os.getenv("BOTTED_MAX_EXECUTORS"))
        
        if os.getenv("BOTTED_MAX_VERIFIERS"):
            config.max_workers_per_type[WorkerType.VERIFIER] = int(os.getenv("BOTTED_MAX_VERIFIERS"))
        
        # Monitoring configuration
        if os.getenv("BOTTED_ENABLE_MONITORING"):
            config.enable_monitoring = os.getenv("BOTTED_ENABLE_MONITORING").lower() == "true"
        
        if os.getenv("BOTTED_MONITORING_INTERVAL"):
            config.monitoring_interval = int(os.getenv("BOTTED_MONITORING_INTERVAL"))
        
        if os.getenv("BOTTED_LOG_LEVEL"):
            config.log_level = os.getenv("BOTTED_LOG_LEVEL")
        
        # Plugin configuration
        if os.getenv("BOTTED_PLUGIN_DIRS"):
            config.plugin_directories = os.getenv("BOTTED_PLUGIN_DIRS").split(":")
        
        if os.getenv("BOTTED_AUTO_LOAD_PLUGINS"):
            config.auto_load_plugins = os.getenv("BOTTED_AUTO_LOAD_PLUGINS").lower() == "true"
        
        return config
    
    def _load_from_file(self, config: SystemConfiguration, config_file: str) -> SystemConfiguration:
        """Load configuration from file"""
        try:
            import json
            
            config_path = Path(config_file)
            if not config_path.exists():
                self.logger.warning(f"Configuration file not found: {config_file}")
                return config
            
            with open(config_path, 'r') as f:
                file_config = json.load(f)
            
            # Apply file configuration
            for key, value in file_config.items():
                if hasattr(config, key):
                    setattr(config, key, value)
                else:
                    self.logger.warning(f"Unknown configuration key: {key}")
            
            self.logger.info(f"Configuration loaded from file: {config_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration file {config_file}: {e}")
        
        return config
    
    def _apply_startup_options(self, config: SystemConfiguration) -> SystemConfiguration:
        """Apply startup options to configuration"""
        if not self.options.enable_monitoring:
            config.enable_monitoring = False
        
        if not self.options.enable_error_recovery:
            config.enable_error_recovery = False
        
        if not self.options.load_plugins:
            config.auto_load_plugins = False
        
        config.log_level = self.options.log_level
        
        return config
    
    async def start_system(self) -> SystemIntegration:
        """
        Start the complete v2 system
        """
        self.logger.info("Starting Botted Library v2 system...")
        
        # Load configuration
        if not self.config:
            self.load_configuration()
        
        # Get system integration instance
        self.system = get_system_integration(self.config)
        
        # Initialize system
        success = await self.system.initialize_system()
        if not success:
            raise RuntimeError("Failed to initialize system")
        
        self.logger.info("System started successfully")
        
        # Print startup summary
        self._print_startup_summary()
        
        return self.system
    
    def _print_startup_summary(self):
        """Print startup summary"""
        if not self.system or not self.config:
            return
        
        status = self.system.get_system_status()
        
        print("\n" + "="*60)
        print("🤖 Botted Library v2 - Collaborative AI Workers")
        print("="*60)
        print(f"Status: {status['state'].upper()}")
        print(f"Server: {self.config.server_host}:{self.config.server_port}")
        print(f"Max Workers: P:{self.config.max_workers_per_type[WorkerType.PLANNER]} "
              f"E:{self.config.max_workers_per_type[WorkerType.EXECUTOR]} "
              f"V:{self.config.max_workers_per_type[WorkerType.VERIFIER]}")
        print(f"Monitoring: {'Enabled' if self.config.enable_monitoring else 'Disabled'}")
        print(f"Error Recovery: {'Enabled' if self.config.enable_error_recovery else 'Disabled'}")
        print(f"Plugins: {'Auto-load' if self.config.auto_load_plugins else 'Manual'}")
        print("="*60)
        print("System ready for collaborative AI work! 🚀")
        print("="*60 + "\n")
    
    def validate_system_requirements(self) -> bool:
        """
        Validate system requirements before startup
        """
        self.logger.info("Validating system requirements...")
        
        # Check Python version
        if sys.version_info < (3, 8):
            self.logger.error("Python 3.8 or higher is required")
            return False
        
        # Check required packages
        required_packages = [
            "asyncio", "threading", "logging", "dataclasses", "enum", "pathlib"
        ]
        
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                self.logger.error(f"Required package not found: {package}")
                return False
        
        # Check system resources
        try:
            import psutil
            
            # Check available memory (minimum 1GB)
            available_memory = psutil.virtual_memory().available
            if available_memory < 1024 * 1024 * 1024:  # 1GB
                self.logger.warning("Low available memory detected")
            
            # Check CPU cores
            cpu_count = psutil.cpu_count()
            if cpu_count < 2:
                self.logger.warning("Limited CPU cores detected")
            
        except ImportError:
            self.logger.info("psutil not available, skipping resource checks")
        
        # Check network connectivity for server
        if self.options.auto_start_server:
            try:
                import socket
                
                # Test if port is available
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex((self.config.server_host if self.config else "localhost", 
                                        self.config.server_port if self.config else 8765))
                sock.close()
                
                if result == 0:
                    self.logger.warning("Server port appears to be in use")
                
            except Exception as e:
                self.logger.warning(f"Network connectivity check failed: {e}")
        
        self.logger.info("System requirements validation completed")
        return True
    
    async def stop_system(self) -> bool:
        """
        Stop the system gracefully
        """
        if not self.system:
            self.logger.warning("No system to stop")
            return True
        
        self.logger.info("Stopping system...")
        success = await self.system.shutdown_system()
        
        if success:
            self.logger.info("System stopped successfully")
        else:
            self.logger.error("System stop failed")
        
        return success


def create_default_startup() -> SystemStartup:
    """Create startup with default options"""
    return SystemStartup()


def create_production_startup() -> SystemStartup:
    """Create startup with production options"""
    options = StartupOptions(
        environment="production",
        log_level="WARNING",
        enable_monitoring=True,
        enable_error_recovery=True,
        background_mode=True
    )
    return SystemStartup(options)


def create_development_startup() -> SystemStartup:
    """Create startup with development options"""
    options = StartupOptions(
        environment="development",
        log_level="DEBUG",
        enable_monitoring=True,
        enable_error_recovery=True,
        background_mode=False
    )
    return SystemStartup(options)


async def quick_start_system(config_file: Optional[str] = None) -> SystemIntegration:
    """
    Quick start the system with minimal configuration
    """
    startup = create_default_startup()
    
    if config_file:
        startup.options.config_file = config_file
    
    # Validate requirements
    if not startup.validate_system_requirements():
        raise RuntimeError("System requirements validation failed")
    
    # Start system
    return await startup.start_system()