"""
IB Simulator TCP Socket Server
Main server that listens for IB API client connections
"""

import asyncio
import logging
import struct
import os
from typing import Dict, List, Optional
from datetime import datetime
import yaml

from ..protocol.encoder import MessageEncoder
from ..protocol.decoder import MessageDecoder
from ..protocol.message_ids import IncomingMessageIds, OutgoingMessageIds, ErrorCodes
from ..database.db_manager import DatabaseManager
from .client_handler import ClientHandler

logger = logging.getLogger(__name__)


class IBSimulatorServer:
    """Main TCP server for IB API simulator"""
    
    def __init__(self, config_path: str = None, env: str = None):
        """Initialize server with configuration"""
        self.config = self._load_config(config_path, env)
        self.db_manager = DatabaseManager(self.config)
        self.encoder = MessageEncoder(self.config['protocol']['encoding'])
        self.decoder = MessageDecoder(self.config['protocol']['encoding'])
        
        # Server settings from config
        self.host = self._get_host_from_config(env)
        self.port = self._get_port_from_config(env)
        self.max_clients = self.config['server']['max_clients']
        
        # Client management
        self.clients: Dict[int, ClientHandler] = {}
        self.next_client_id = 1
        self.server = None
        self.running = False
        
        # Market data manager (to be implemented)
        self.market_data_manager = None
        
        logger.info(f"IB Simulator Server initialized - {self.host}:{self.port}")
    
    def _load_config(self, config_path: str = None, env: str = None) -> Dict:
        """Load configuration from file with environment overrides"""
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Apply environment variable overrides
        self._apply_env_overrides(config)
        
        return config
    
    def _apply_env_overrides(self, config: Dict):
        """Apply environment variable overrides to config"""
        # Server settings
        if os.getenv('IB_SIM_HOST'):
            config['server']['host'] = os.getenv('IB_SIM_HOST')
        if os.getenv('IB_SIM_PORT'):
            config['server']['port'] = int(os.getenv('IB_SIM_PORT'))
        
        # Database settings
        if os.getenv('IB_SIM_DB_PATH'):
            config['database']['path'] = os.getenv('IB_SIM_DB_PATH')
        
        # You can add more overrides as needed
    
    def _get_host_from_config(self, env: str = None) -> str:
        """Get host from config based on environment"""
        if env and env in self.config['server']['environments']:
            return self.config['server']['environments'][env]['host']
        return self.config['server']['host']
    
    def _get_port_from_config(self, env: str = None) -> int:
        """Get port from config based on environment"""
        if env and env in self.config['server']['environments']:
            return self.config['server']['environments'][env]['port']
        return self.config['server']['port']
    
    async def start(self):
        """Start the TCP server"""
        try:
            self.server = await asyncio.start_server(
                self.handle_client,
                self.host,
                self.port,
                reuse_address=True
            )
            
            self.running = True
            
            addrs = ', '.join(str(sock.getsockname()) for sock in self.server.sockets)
            logger.info(f"IB Simulator Server listening on {addrs}")
            logger.info(f"Ready to accept IB API client connections")
            logger.info(f"Paper trading port: {self.port}")
            
            async with self.server:
                await self.server.serve_forever()
                
        except Exception as e:
            logger.error(f"Server start failed: {e}")
            raise
    
    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle new client connection"""
        client_address = writer.get_extra_info('peername')
        client_id = self.next_client_id
        self.next_client_id += 1
        
        logger.info(f"New connection from {client_address} - Client ID: {client_id}")
        
        # Check max clients limit
        if len(self.clients) >= self.max_clients:
            logger.warning(f"Max clients reached ({self.max_clients}), rejecting connection")
            writer.close()
            await writer.wait_closed()
            return
        
        # Create client handler
        client_handler = ClientHandler(
            client_id=client_id,
            reader=reader,
            writer=writer,
            server=self,
            config=self.config
        )
        
        self.clients[client_id] = client_handler
        
        try:
            # Handle client communication
            await client_handler.handle()
        except Exception as e:
            logger.error(f"Client {client_id} error: {e}")
        finally:
            # Clean up
            if client_id in self.clients:
                del self.clients[client_id]
            logger.info(f"Client {client_id} disconnected")
    
    def broadcast_market_data(self, symbol: str, data: Dict):
        """Broadcast market data to all subscribed clients"""
        for client in self.clients.values():
            if client.is_subscribed_to_symbol(symbol):
                asyncio.create_task(client.send_market_data(symbol, data))
    
    def get_next_order_id(self) -> int:
        """Get next valid order ID"""
        # In real implementation, this would be properly synchronized
        return 1000 + len(self.clients) * 1000 + int(datetime.now().timestamp() % 1000)
    
    async def stop(self):
        """Stop the server gracefully"""
        logger.info("Stopping IB Simulator Server...")
        self.running = False
        
        # Close all client connections
        for client in list(self.clients.values()):
            await client.close()
        
        # Close server
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        # Close database
        self.db_manager.close()
        
        logger.info("IB Simulator Server stopped")


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='IB API Simulator Server')
    parser.add_argument('--config', help='Path to config file', default=None)
    parser.add_argument('--env', help='Environment (local, docker, network)', default=None)
    parser.add_argument('--host', help='Override host from config', default=None)
    parser.add_argument('--port', help='Override port from config', type=int, default=None)
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Apply command line overrides
    if args.host:
        os.environ['IB_SIM_HOST'] = args.host
    if args.port:
        os.environ['IB_SIM_PORT'] = str(args.port)
    
    # Create and start server
    server = IBSimulatorServer(config_path=args.config, env=args.env)
    
    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        await server.stop()


if __name__ == '__main__':
    asyncio.run(main())