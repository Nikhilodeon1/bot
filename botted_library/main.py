#!/usr/bin/env python3
"""
Main entry point for Botted Library v2 Collaborative System

This module provides command-line interface and programmatic entry points
for starting and managing the v2 collaborative system.
"""

import argparse
import asyncio
import json
import logging
import signal
import sys
from pathlib import Path
from typing import Optional

from .core.system_startup import (
    SystemStartup, StartupOptions, create_default_startup,
    create_production_startup, create_development_startup
)
from .core.system_integration import SystemConfiguration


def setup_signal_handlers(startup: SystemStartup):
    """Setup signal handlers for graceful shutdown"""
    def signal_handler(signum, frame):
        print(f"\nReceived signal {signum}, shutting down gracefully...")
        if startup.system:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(startup.stop_system())
            finally:
                loop.close()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def create_sample_config(output_path: str):
    """Create a sample configuration file"""
    config = {
        "server_host": "localhost",
        "server_port": 8765,
        "server_max_connections": 100,
        "max_workers_per_type": {
            "PLANNER": 5,
            "EXECUTOR": 20,
            "VERIFIER": 10
        },
        "max_collaborative_spaces": 50,
        "max_participants_per_space": 20,
        "plugin_directories": ["plugins", "~/.botted_library/plugins"],
        "auto_load_plugins": True,
        "tool_timeout": 300,
        "max_concurrent_tools": 10,
        "enable_monitoring": True,
        "monitoring_interval": 30,
        "log_level": "INFO",
        "enable_error_recovery": True,
        "max_retry_attempts": 3,
        "retry_delay": 1.0,
        "message_queue_size": 1000,
        "worker_heartbeat_interval": 60,
        "cleanup_interval": 300
    }
    
    with open(output_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"Sample configuration created at: {output_path}")


async def start_interactive_mode(startup: SystemStartup):
    """Start interactive mode for system management"""
    system = await startup.start_system()
    
    print("\n🤖 Botted Library v2 - Interactive Mode")
    print("Type 'help' for available commands, 'quit' to exit")
    
    while True:
        try:
            command = input("\nbotted> ").strip().lower()
            
            if command in ['quit', 'exit', 'q']:
                break
            elif command == 'help':
                print_help()
            elif command == 'status':
                print_status(system)
            elif command == 'workers':
                print_workers(system)
            elif command == 'spaces':
                print_spaces(system)
            elif command == 'metrics':
                print_metrics(system)
            elif command.startswith('create worker'):
                await handle_create_worker(system, command)
            elif command.startswith('create space'):
                await handle_create_space(system, command)
            else:
                print(f"Unknown command: {command}. Type 'help' for available commands.")
        
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
    
    await startup.stop_system()


def print_help():
    """Print available commands"""
    print("\nAvailable commands:")
    print("  help                    - Show this help message")
    print("  status                  - Show system status")
    print("  workers                 - List active workers")
    print("  spaces                  - List collaborative spaces")
    print("  metrics                 - Show system metrics")
    print("  create worker <type>    - Create a new worker (planner/executor/verifier)")
    print("  create space <name>     - Create a collaborative space")
    print("  quit                    - Exit interactive mode")


def print_status(system):
    """Print system status"""
    status = system.get_system_status()
    print(f"\nSystem Status: {status['state'].upper()}")
    
    if 'components' in status:
        print("\nComponents:")
        for name, component_status in status['components'].items():
            print(f"  {name}: {component_status.get('status', 'unknown')}")
    
    if 'configuration' in status:
        config = status['configuration']
        print(f"\nConfiguration:")
        print(f"  Server: {config['server_host']}:{config['server_port']}")
        print(f"  Monitoring: {'Enabled' if config['monitoring_enabled'] else 'Disabled'}")
        print(f"  Error Recovery: {'Enabled' if config['error_recovery_enabled'] else 'Disabled'}")


def print_workers(system):
    """Print active workers"""
    registry = system.get_worker_registry()
    if not registry:
        print("Worker registry not available")
        return
    
    workers = registry.get_all_workers()
    if not workers:
        print("No active workers")
        return
    
    print(f"\nActive Workers ({len(workers)}):")
    for worker in workers:
        print(f"  {worker.worker_id}: {worker.name} ({worker.worker_type.value})")


def print_spaces(system):
    """Print collaborative spaces"""
    server = system.get_server()
    if not server:
        print("Server not available")
        return
    
    spaces = server.get_collaborative_spaces()
    if not spaces:
        print("No collaborative spaces")
        return
    
    print(f"\nCollaborative Spaces ({len(spaces)}):")
    for space in spaces:
        participants = len(space.get_participants())
        print(f"  {space.space_id}: {participants} participants")


def print_metrics(system):
    """Print system metrics"""
    status = system.get_system_status()
    metrics = status.get('metrics', {})
    
    if not metrics:
        print("No metrics available")
        return
    
    print("\nSystem Metrics:")
    for key, value in metrics.items():
        print(f"  {key}: {value}")


async def handle_create_worker(system, command):
    """Handle create worker command"""
    parts = command.split()
    if len(parts) < 3:
        print("Usage: create worker <type>")
        return
    
    worker_type = parts[2].upper()
    if worker_type not in ['PLANNER', 'EXECUTOR', 'VERIFIER']:
        print("Worker type must be: planner, executor, or verifier")
        return
    
    # This would need to be implemented in the system
    print(f"Creating {worker_type} worker... (not implemented in demo)")


async def handle_create_space(system, command):
    """Handle create space command"""
    parts = command.split()
    if len(parts) < 3:
        print("Usage: create space <name>")
        return
    
    space_name = parts[2]
    # This would need to be implemented in the system
    print(f"Creating collaborative space '{space_name}'... (not implemented in demo)")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Botted Library v2 - Collaborative AI Workers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m botted_library.main start                    # Start with default settings
  python -m botted_library.main start --config config.json  # Start with config file
  python -m botted_library.main start --production       # Start in production mode
  python -m botted_library.main interactive              # Start interactive mode
  python -m botted_library.main create-config config.json   # Create sample config
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Start command
    start_parser = subparsers.add_parser('start', help='Start the collaborative system')
    start_parser.add_argument('--config', '-c', help='Configuration file path')
    start_parser.add_argument('--production', '-p', action='store_true', 
                             help='Use production settings')
    start_parser.add_argument('--development', '-d', action='store_true',
                             help='Use development settings')
    start_parser.add_argument('--log-level', default='INFO',
                             choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                             help='Set log level')
    start_parser.add_argument('--no-monitoring', action='store_true',
                             help='Disable monitoring')
    start_parser.add_argument('--no-error-recovery', action='store_true',
                             help='Disable error recovery')
    start_parser.add_argument('--no-plugins', action='store_true',
                             help='Disable plugin loading')
    
    # Interactive command
    interactive_parser = subparsers.add_parser('interactive', help='Start interactive mode')
    interactive_parser.add_argument('--config', '-c', help='Configuration file path')
    
    # Create config command
    config_parser = subparsers.add_parser('create-config', help='Create sample configuration')
    config_parser.add_argument('output', help='Output file path')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show system status')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == 'create-config':
        create_sample_config(args.output)
        return
    
    if args.command == 'status':
        # This would check if system is running and show status
        print("System status checking not implemented in demo")
        return
    
    # Create startup based on arguments
    if args.command in ['start', 'interactive']:
        if hasattr(args, 'production') and args.production:
            startup = create_production_startup()
        elif hasattr(args, 'development') and args.development:
            startup = create_development_startup()
        else:
            startup = create_default_startup()
        
        # Apply command line options
        if hasattr(args, 'config') and args.config:
            startup.options.config_file = args.config
        
        if hasattr(args, 'log_level'):
            startup.options.log_level = args.log_level
        
        if hasattr(args, 'no_monitoring') and args.no_monitoring:
            startup.options.enable_monitoring = False
        
        if hasattr(args, 'no_error_recovery') and args.no_error_recovery:
            startup.options.enable_error_recovery = False
        
        if hasattr(args, 'no_plugins') and args.no_plugins:
            startup.options.load_plugins = False
        
        # Setup signal handlers
        setup_signal_handlers(startup)
        
        # Validate requirements
        if not startup.validate_system_requirements():
            print("❌ System requirements validation failed")
            sys.exit(1)
        
        # Start system
        try:
            if args.command == 'interactive':
                asyncio.run(start_interactive_mode(startup))
            else:
                # Start and keep running
                system = asyncio.run(startup.start_system())
                print("System started. Press Ctrl+C to stop.")
                
                # Keep running until interrupted
                try:
                    while True:
                        asyncio.run(asyncio.sleep(1))
                except KeyboardInterrupt:
                    print("\nShutting down...")
                    asyncio.run(startup.stop_system())
        
        except Exception as e:
            print(f"❌ Failed to start system: {e}")
            sys.exit(1)


if __name__ == '__main__':
    main()