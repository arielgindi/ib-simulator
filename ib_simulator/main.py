#!/usr/bin/env python3
"""
Interactive Brokers API Simulator
Main entry point for the IB API simulator server
"""

import asyncio
import logging
import sys
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from ib_simulator.core.server import IBSimulatorServer


def setup_logging(level: str = "INFO"):
    """Set up logging configuration"""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("ib_simulator.log")
        ]
    )
    
    # Set specific loggers
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def print_banner():
    """Print startup banner"""
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║        Interactive Brokers API Simulator                     ║
    ║        Paper Trading Environment                             ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Interactive Brokers API Simulator Server',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables:
  IB_SIM_HOST      Override server host
  IB_SIM_PORT      Override server port
  IB_SIM_DB_PATH   Override database path

Examples:
  # Run with default settings
  python main.py
  
  # Run with custom host/port
  python main.py --host 192.168.1.100 --port 7497
  
  # Run with environment config
  python main.py --env network
  
  # Run with custom config file
  python main.py --config /path/to/config.yaml
        """
    )
    
    parser.add_argument(
        '--config', 
        help='Path to configuration file',
        default=None
    )
    
    parser.add_argument(
        '--env',
        help='Environment configuration (local, docker, network)',
        choices=['local', 'docker', 'network'],
        default=None
    )
    
    parser.add_argument(
        '--host',
        help='Server host address (overrides config)',
        default=None
    )
    
    parser.add_argument(
        '--port',
        help='Server port (overrides config)',
        type=int,
        default=None
    )
    
    parser.add_argument(
        '--log-level',
        help='Logging level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO'
    )
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    # Print banner
    print_banner()
    
    # Apply command line overrides to environment
    if args.host:
        import os
        os.environ['IB_SIM_HOST'] = args.host
        logger.info(f"Host override: {args.host}")
    
    if args.port:
        import os
        os.environ['IB_SIM_PORT'] = str(args.port)
        logger.info(f"Port override: {args.port}")
    
    # Create and start server
    server = None
    try:
        logger.info("Starting IB API Simulator Server...")
        
        server = IBSimulatorServer(
            config_path=args.config,
            env=args.env
        )
        
        # Start server
        await server.start()
        
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if server is not None:
            await server.stop()
        logger.info("Server shutdown complete")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown requested")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)