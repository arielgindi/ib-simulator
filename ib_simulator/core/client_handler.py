"""
Client Handler for IB Simulator
Handles individual client connections and message processing
"""

import asyncio
import struct
import logging
from typing import Dict, List, Optional, Set, Any
from datetime import datetime
import time

from ..protocol.encoder import MessageEncoder
from ..protocol.decoder import MessageDecoder
from ..protocol.message_ids import IncomingMessageIds, OutgoingMessageIds, ErrorCodes

logger = logging.getLogger(__name__)


class ClientHandler:
    """Handles individual IB API client connections"""
    
    def __init__(self, client_id: int, reader: asyncio.StreamReader,
                 writer: asyncio.StreamWriter, server, config: Dict):
        self.client_id = client_id
        self.reader = reader
        self.writer = writer
        self.server = server
        self.config = config
        
        # Protocol handlers
        self.encoder = MessageEncoder(config['protocol']['encoding'])
        self.decoder = MessageDecoder(config['protocol']['encoding'])
        
        # Connection state
        self.api_connected = False
        self.server_version = config['protocol']['version']
        self.client_version = None
        self.connection_time = datetime.now()
        
        # Authentication state
        self.authenticated = False
        self.account_id = None
        self.username = None
        
        # Subscriptions
        self.market_data_subscriptions: Dict[int, Dict] = {}  # req_id -> subscription info
        self.account_subscriptions: Set[str] = set()
        self.position_subscriptions: Set[str] = set()
        
        # Order management
        self.next_order_id = None
        
        # Rate limiting
        self.last_message_time = time.time()
        self.message_count = 0
        self.rate_limit_window = 1.0  # 1 second window
        
        logger.info(f"Client handler created for client {client_id}")
    
    async def handle(self):
        """Main client handling loop"""
        try:
            # IB protocol starts with version exchange
            await self._handle_initial_handshake()
            
            # Message processing loop
            buffer = b''
            while True:
                # Read data from client
                data = await self.reader.read(self.config['server']['buffer_size'])
                if not data:
                    break
                
                buffer += data
                
                # Process complete messages
                while len(buffer) >= 4:
                    # Check message length
                    msg_length = struct.unpack('>I', buffer[:4])[0]
                    
                    if len(buffer) < 4 + msg_length:
                        # Incomplete message
                        break
                    
                    # Extract complete message
                    message_data = buffer[:4 + msg_length]
                    buffer = buffer[4 + msg_length:]
                    
                    # Process message
                    await self._process_message(message_data)
        
        except asyncio.CancelledError:
            logger.info(f"Client {self.client_id} handler cancelled")
        except Exception as e:
            logger.error(f"Client {self.client_id} error: {e}", exc_info=True)
        finally:
            await self.close()
    
    async def _handle_initial_handshake(self):
        """Handle IB API initial handshake"""
        try:
            # Wait for client version
            data = await self.reader.read(1024)
            if not data:
                return
            
            # IB sends "API\0" prefix followed by version
            if data.startswith(b'API\x00'):
                # Extract version info
                parts = data.split(b'\x00')
                if len(parts) >= 2:
                    try:
                        # Parse client version - it might be 'v' + version or just version
                        version_str = parts[1].decode('latin-1')
                        if version_str.startswith('v'):
                            version_str = version_str[1:]
                        
                        # Handle version range like "100..176"
                        if '..' in version_str:
                            min_ver, max_ver = version_str.split('..')
                            self.client_version = int(max_ver)
                        else:
                            self.client_version = int(version_str)
                    except:
                        self.client_version = 100  # Default fallback
            
            # Send server version
            await self._send_raw(self.encoder.server_version(
                self.server_version,
                self.connection_time.strftime('%Y%m%d %H:%M:%S')
            ))
            
            # Mark as connected
            self.api_connected = True
            logger.info(f"Client {self.client_id} handshake complete - Client version: {self.client_version}")
            
        except Exception as e:
            logger.error(f"Handshake failed for client {self.client_id}: {e}")
            raise
    
    async def _process_message(self, data: bytes):
        """Process a complete message from client"""
        try:
            # Check rate limit
            if not self._check_rate_limit():
                await self._send_error(-1, ErrorCodes.MAX_RATE_EXCEEDED, 
                                     "Max message rate exceeded")
                return
            
            # Decode message
            msg_id, fields = self.decoder.decode_message(data)
            
            if msg_id is None:
                logger.warning(f"Failed to decode message from client {self.client_id}")
                return
            
            logger.debug(f"Client {self.client_id} - Message ID: {msg_id}, Fields: {fields[:5]}...")
            
            # Route to appropriate handler
            await self._route_message(msg_id, fields)
            
        except Exception as e:
            logger.error(f"Message processing error for client {self.client_id}: {e}")
            await self._send_error(-1, ErrorCodes.SERVER_ERROR, str(e))
    
    def _check_rate_limit(self) -> bool:
        """Check if client is within rate limits"""
        current_time = time.time()
        
        # Reset window if needed
        if current_time - self.last_message_time > self.rate_limit_window:
            self.message_count = 0
            self.last_message_time = current_time
        
        self.message_count += 1
        
        # Check limit
        max_rate = self.config['protocol']['message_rate_limit']
        return self.message_count <= max_rate
    
    async def _route_message(self, msg_id: int, fields: List[str]):
        """Route message to appropriate handler"""
        handlers = {
            IncomingMessageIds.START_API: self._handle_start_api,
            IncomingMessageIds.REQ_IDS: self._handle_req_ids,
            IncomingMessageIds.REQ_MANAGED_ACCTS: self._handle_req_managed_accounts,
            IncomingMessageIds.REQ_ACCT_DATA: self._handle_req_account_data,
            IncomingMessageIds.REQ_POSITIONS: self._handle_req_positions,
            IncomingMessageIds.REQ_MKT_DATA: self._handle_req_market_data,
            IncomingMessageIds.CANCEL_MKT_DATA: self._handle_cancel_market_data,
            IncomingMessageIds.PLACE_ORDER: self._handle_place_order,
            IncomingMessageIds.CANCEL_ORDER: self._handle_cancel_order,
            IncomingMessageIds.REQ_OPEN_ORDERS: self._handle_req_open_orders,
            IncomingMessageIds.REQ_CONTRACT_DATA: self._handle_req_contract_details,
            IncomingMessageIds.REQ_SEC_DEF_OPT_PARAMS: self._handle_req_option_params,
            IncomingMessageIds.REQ_CURRENT_TIME: self._handle_req_current_time,
            IncomingMessageIds.REQ_EXECUTIONS: self._handle_req_executions,
            IncomingMessageIds.REQ_HISTORICAL_DATA: self._handle_req_historical_data,
        }
        
        handler = handlers.get(msg_id)
        if handler:
            parsed_data = self.decoder.parse_message(msg_id, fields)
            await handler(parsed_data)
        else:
            logger.warning(f"No handler for message ID {msg_id}")
            await self._send_error(-1, ErrorCodes.UNKNOWN_ID, 
                                 f"Unknown message ID: {msg_id}")
    
    # Message handlers
    async def _handle_start_api(self, data: Dict):
        """Handle START_API message"""
        logger.info(f"Client {self.client_id} START_API: {data}")
        
        # Set client ID if provided
        if data.get('client_id') is not None:
            self.client_id = data['client_id']
        
        # Send initial connection messages
        await self._send_next_valid_id()
        await self._send_managed_accounts()
    
    async def _handle_req_ids(self, data: Dict):
        """Handle request for next valid order ID"""
        await self._send_next_valid_id()
    
    async def _handle_req_managed_accounts(self, data: Dict):
        """Handle request for managed accounts"""
        await self._send_managed_accounts()
    
    async def _handle_req_account_data(self, data: Dict):
        """Handle request for account data"""
        account_code = data.get('account_code', '')
        subscribe = data.get('subscribe', True)
        
        # For simulator, use the configured test account
        if not account_code:
            account_code = self.config['authentication']['accounts'][0]['account_id']
        
        if subscribe:
            self.account_subscriptions.add(account_code)
            await self._send_account_updates(account_code)
        else:
            self.account_subscriptions.discard(account_code)
            await self._send_account_download_end(account_code)
    
    async def _handle_req_positions(self, data: Dict):
        """Handle request for positions"""
        # Get first configured account
        account_id = self.config['authentication']['accounts'][0]['account_id']
        
        # Send positions from database
        positions = self.server.db_manager.get_positions(account_id)
        
        for position in positions:
            await self._send_position_data(account_id, position)
        
        # Send end marker
        await self._send_raw(self.encoder.position_end())
    
    async def _handle_req_market_data(self, data: Dict):
        """Handle market data subscription request"""
        req_id = data.get('req_id', -1)
        contract = data.get('contract', {})
        
        # Store subscription
        self.market_data_subscriptions[req_id] = {
            'contract': contract,
            'generic_ticks': data.get('generic_tick_list', ''),
            'snapshot': data.get('snapshot', False),
            'regulatory_snapshot': data.get('regulatory_snapshot', False)
        }
        
        # Send initial market data
        await self._send_initial_market_data(req_id, contract)
    
    async def _handle_cancel_market_data(self, data: Dict):
        """Handle cancel market data request"""
        req_id = data.get('req_id', -1)
        
        if req_id in self.market_data_subscriptions:
            del self.market_data_subscriptions[req_id]
            logger.info(f"Cancelled market data subscription {req_id}")
    
    async def _handle_place_order(self, data: Dict):
        """Handle place order request"""
        order_data = {
            'account_id': self.config['authentication']['accounts'][0]['account_id'],
            'client_id': self.client_id,
            'con_id': data['contract'].get('con_id', 0),
            'symbol': data['contract']['symbol'],
            'security_type': data['contract']['sec_type'],
            'action': data['order']['action'],
            'order_type': data['order']['order_type'],
            'quantity': data['order']['total_quantity'],
            'limit_price': data['order'].get('limit_price'),
            'aux_price': data['order'].get('aux_price'),
            'time_in_force': data['order'].get('tif', 'DAY')
        }
        
        # Create order in database
        order_id = data['order_id']
        
        # Send order status updates
        await self._send_order_status(order_id, 'PendingSubmit', 0, 0, 0)
        await asyncio.sleep(0.1)  # Simulate processing
        await self._send_order_status(order_id, 'Submitted', 0, 0, 0)
        
        # TODO: Implement order execution logic
    
    async def _handle_cancel_order(self, data: Dict):
        """Handle cancel order request"""
        order_id = data.get('order_id', -1)
        
        # Send cancellation status
        await self._send_order_status(order_id, 'PendingCancel', 0, 0, 0)
        await asyncio.sleep(0.1)
        await self._send_order_status(order_id, 'Cancelled', 0, 0, 0)
    
    async def _handle_req_open_orders(self, data: Dict):
        """Handle request for open orders"""
        account_id = self.config['authentication']['accounts'][0]['account_id']
        
        # Get open orders from database
        orders = self.server.db_manager.get_open_orders(account_id)
        
        # Send each order
        for order in orders:
            # TODO: Send full order details
            pass
        
        # Send end marker
        await self._send_raw(self.encoder.open_order_end())
    
    async def _handle_req_contract_details(self, data: Dict):
        """Handle request for contract details"""
        req_id = data.get('req_id', -1)
        contract = data.get('contract', {})
        
        # For simulator, return simple contract details
        if contract.get('symbol'):
            contract_info = self.server.db_manager.get_contract_by_symbol(
                contract['symbol'], 
                contract.get('sec_type', 'STK')
            )
            
            if contract_info:
                # Send contract data
                await self._send_contract_details(req_id, contract_info)
        
        # Send end marker
        await self._send_raw(self.encoder.contract_data_end(req_id))
    
    async def _handle_req_option_params(self, data: Dict):
        """Handle request for option chain parameters"""
        req_id = data.get('req_id', -1)
        underlying_symbol = data.get('underlying_symbol', '')
        
        # For simulator, generate sample option chain
        # TODO: Implement full option chain generation
        
        # Send end marker
        await self._send_raw(self.encoder.security_definition_option_parameter_end(req_id))
    
    async def _handle_req_current_time(self, data: Dict):
        """Handle request for current server time"""
        current_time = int(time.time())
        await self._send_raw(self.encoder.current_time(current_time))
    
    async def _handle_req_executions(self, data: Dict):
        """Handle request for executions"""
        req_id = data.get('req_id', -1)
        
        # TODO: Implement execution filtering and retrieval
        
        # Send end marker
        await self._send_raw(self.encoder.execution_data_end(req_id))
    
    async def _handle_req_historical_data(self, data: Dict):
        """Handle request for historical data"""
        req_id = data.get('req_id', -1)
        
        # TODO: Implement historical data generation
        
        # For now, send empty result
        await self._send_raw(self.encoder.historical_data(
            req_id, '', '', 0, []
        ))
    
    # Helper methods
    async def _send_next_valid_id(self):
        """Send next valid order ID"""
        self.next_order_id = self.server.get_next_order_id()
        await self._send_raw(self.encoder.next_valid_id(self.next_order_id))
    
    async def _send_managed_accounts(self):
        """Send list of managed accounts"""
        # Get configured accounts
        accounts = [acc['account_id'] for acc in self.config['authentication']['accounts']]
        accounts_str = ','.join(accounts)
        await self._send_raw(self.encoder.managed_accounts(accounts_str))
    
    async def _send_account_updates(self, account_id: str):
        """Send account value updates"""
        account_data = self.server.db_manager.get_account_summary(account_id)
        
        if account_data:
            # Send various account values
            currency = account_data.get('base_currency', 'USD')
            
            await self._send_raw(self.encoder.account_value(
                'NetLiquidation', str(account_data['net_liquidation']), 
                currency, account_id
            ))
            
            await self._send_raw(self.encoder.account_value(
                'TotalCashValue', str(account_data['cash_balance']), 
                currency, account_id
            ))
            
            await self._send_raw(self.encoder.account_value(
                'UnrealizedPnL', str(account_data['unrealized_pnl']), 
                currency, account_id
            ))
            
            await self._send_raw(self.encoder.account_value(
                'RealizedPnL', str(account_data['realized_pnl']), 
                currency, account_id
            ))
            
            # Send timestamp
            await self._send_raw(self.encoder.account_update_time(
                datetime.now().strftime('%H:%M:%S')
            ))
        
        # Send portfolio positions
        positions = self.server.db_manager.get_positions(account_id)
        for position in positions:
            await self._send_portfolio_position(account_id, position)
        
        # Send end marker
        await self._send_account_download_end(account_id)
    
    async def _send_account_download_end(self, account_id: str):
        """Send account download end marker"""
        await self._send_raw(self.encoder.account_download_end(account_id))
    
    async def _send_portfolio_position(self, account_id: str, position: Dict):
        """Send portfolio position update"""
        await self._send_raw(self.encoder.portfolio_value(
            position['con_id'],
            position['symbol'],
            position['security_type'],
            '',  # expiry
            0,   # strike
            '',  # right
            1,   # multiplier
            '',  # primary exchange
            position['currency'],
            position['symbol'],  # local symbol
            position['symbol'],  # trading class
            position['position'],
            position['market_price'],
            position['market_value'],
            position['avg_cost'],
            position['unrealized_pnl'],
            position['realized_pnl'],
            account_id
        ))
    
    async def _send_position_data(self, account_id: str, position: Dict):
        """Send position data"""
        await self._send_raw(self.encoder.position_data(
            account_id,
            position['con_id'],
            position['symbol'],
            position['security_type'],
            '',  # expiry
            0,   # strike
            '',  # right
            1,   # multiplier
            'SMART',  # exchange
            position['currency'],
            position['symbol'],  # local symbol
            position['symbol'],  # trading class
            position['position'],
            position['avg_cost']
        ))
    
    async def _send_initial_market_data(self, req_id: int, contract: Dict):
        """Send initial market data for a contract"""
        symbol = contract.get('symbol', '')
        
        # Generate sample market data
        base_price = 100.0  # TODO: Get from database or market simulator
        
        # Send various tick types
        await self._send_raw(self.encoder.tick_price(req_id, 1, base_price - 0.01))  # Bid
        await self._send_raw(self.encoder.tick_price(req_id, 2, base_price + 0.01))  # Ask
        await self._send_raw(self.encoder.tick_price(req_id, 4, base_price))         # Last
        
        await self._send_raw(self.encoder.tick_size(req_id, 0, 100))  # Bid size
        await self._send_raw(self.encoder.tick_size(req_id, 3, 100))  # Ask size
        await self._send_raw(self.encoder.tick_size(req_id, 5, 50))   # Last size
        await self._send_raw(self.encoder.tick_size(req_id, 8, 1000000))  # Volume
    
    async def _send_contract_details(self, req_id: int, contract_info: Dict):
        """Send contract details"""
        await self._send_raw(self.encoder.contract_data(
            req_id,
            contract_info['symbol'],
            contract_info['security_type'],
            '',  # expiry
            0,   # strike
            '',  # right
            contract_info['exchange'],
            contract_info['currency'],
            contract_info['local_symbol'],
            contract_info['trading_class'],
            contract_info['con_id'],
            0.01,  # min tick
            1,     # md size multiplier
            contract_info['multiplier'],
            'MKT,LMT,STP,STP_LMT',  # order types
            'SMART,NYSE,NASDAQ',    # valid exchanges
            1,     # price magnifier
            0,     # under con id
            contract_info['symbol'],  # long name
            'SMART',  # primary exchange
            '',    # contract month
            '',    # industry
            '',    # category
            '',    # subcategory
            'EST',  # time zone
            '09:30-16:00',  # trading hours
            '09:30-16:00',  # liquid hours
            '',    # ev rule
            0,     # ev multiplier
            0,     # sec id list count
            [],    # sec id list
            0,     # agg group
            '',    # under symbol
            '',    # under sec type
            '',    # market rule ids
            '',    # real expiration date
            '',    # last trade time
            ''     # stock type
        ))
    
    async def _send_order_status(self, order_id: int, status: str, 
                                filled: float, remaining: float, avg_fill_price: float):
        """Send order status update"""
        await self._send_raw(self.encoder.order_status(
            order_id, status, filled, remaining, avg_fill_price,
            order_id + 1000,  # perm_id
            0,  # parent_id
            avg_fill_price,  # last_fill_price
            self.client_id,
            '',  # why_held
            0    # mkt_cap_price
        ))
    
    async def _send_error(self, req_id: int, error_code: int, error_msg: str):
        """Send error message to client"""
        await self._send_raw(self.encoder.error_message(req_id, error_code, error_msg))
    
    async def _send_raw(self, data: bytes):
        """Send raw data to client"""
        try:
            self.writer.write(data)
            await self.writer.drain()
        except Exception as e:
            logger.error(f"Failed to send data to client {self.client_id}: {e}")
            raise
    
    def is_subscribed_to_symbol(self, symbol: str) -> bool:
        """Check if client is subscribed to symbol"""
        for sub in self.market_data_subscriptions.values():
            if sub['contract'].get('symbol') == symbol:
                return True
        return False
    
    async def send_market_data(self, symbol: str, data: Dict):
        """Send market data update for symbol"""
        # Find matching subscriptions
        for req_id, sub in self.market_data_subscriptions.items():
            if sub['contract'].get('symbol') == symbol:
                # Send price updates
                if 'bid' in data:
                    await self._send_raw(self.encoder.tick_price(req_id, 1, data['bid']))
                if 'ask' in data:
                    await self._send_raw(self.encoder.tick_price(req_id, 2, data['ask']))
                if 'last' in data:
                    await self._send_raw(self.encoder.tick_price(req_id, 4, data['last']))
                
                # Send size updates
                if 'bid_size' in data:
                    await self._send_raw(self.encoder.tick_size(req_id, 0, data['bid_size']))
                if 'ask_size' in data:
                    await self._send_raw(self.encoder.tick_size(req_id, 3, data['ask_size']))
                if 'volume' in data:
                    await self._send_raw(self.encoder.tick_size(req_id, 8, data['volume']))
    
    async def close(self):
        """Close client connection"""
        try:
            self.writer.close()
            await self.writer.wait_closed()
        except Exception as e:
            logger.error(f"Error closing client {self.client_id}: {e}")