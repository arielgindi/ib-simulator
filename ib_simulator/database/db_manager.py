"""
Database Manager for IB Simulator
Handles all database operations with DuckDB
"""

import duckdb
import bcrypt
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import os
from pathlib import Path

from .schema import SCHEMA_SQL, VIEWS_SQL

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages DuckDB database for IB Simulator"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize database manager with configuration"""
        self.config = config
        self.db_path = config['database']['path']
        self.connection = None
        self._ensure_db_directory()
        self._initialize_database()
    
    def _ensure_db_directory(self):
        """Ensure database directory exists"""
        db_dir = Path(self.db_path).parent
        if not db_dir.exists():
            db_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created database directory: {db_dir}")
    
    def _initialize_database(self):
        """Initialize database with schema and initial data"""
        try:
            self.connection = duckdb.connect(self.db_path)
            logger.info(f"Connected to database: {self.db_path}")
            
            # Create schema
            self.connection.execute(SCHEMA_SQL)
            self.connection.execute(VIEWS_SQL)
            logger.info("Database schema created successfully")
            
            # Initialize default data
            self._initialize_default_data()
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    def _initialize_default_data(self):
        """Initialize default accounts and contracts"""
        # Check if accounts already exist
        result = self.connection.execute("SELECT COUNT(*) FROM accounts").fetchone()
        if result[0] > 0:
            logger.info("Database already initialized, skipping default data")
            return
        
        # Create default accounts from config
        for account_config in self.config['authentication']['accounts']:
            self.create_account(
                username=account_config['username'],
                password=account_config['password'],
                account_id=account_config['account_id'],
                account_type=account_config['account_type'],
                initial_balance=account_config['initial_balance'],
                base_currency=account_config.get('base_currency', 'USD')
            )
        
        # Create default contracts for configured symbols
        self._create_default_contracts()
        
        logger.info("Default data initialized successfully")
    
    def create_account(self, username: str, password: str, account_id: str,
                      account_type: str, initial_balance: float, base_currency: str = 'USD'):
        """Create a new account"""
        try:
            # Hash password
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            # Insert account
            self.connection.execute("""
                INSERT INTO accounts (
                    account_id, username, password_hash, account_type,
                    base_currency, net_liquidation, available_funds,
                    buying_power, cash_balance
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                account_id, username, password_hash, account_type,
                base_currency, initial_balance, initial_balance,
                initial_balance * 4,  # 4x buying power for margin
                initial_balance
            ))
            
            logger.info(f"Created account: {account_id} for user: {username}")
            
        except Exception as e:
            logger.error(f"Failed to create account: {e}")
            raise
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate user and return account info"""
        try:
            result = self.connection.execute("""
                SELECT account_id, username, password_hash, account_type,
                       net_liquidation, available_funds
                FROM accounts
                WHERE username = ?
            """, (username,)).fetchone()
            
            if not result:
                return None
            
            # Verify password
            if bcrypt.checkpw(password.encode('utf-8'), result[2].encode('utf-8')):
                return {
                    'account_id': result[0],
                    'username': result[1],
                    'account_type': result[3],
                    'net_liquidation': float(result[4]),
                    'available_funds': float(result[5])
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return None
    
    def _create_default_contracts(self):
        """Create default stock contracts"""
        contracts = []
        con_id = 1000  # Starting contract ID
        
        for symbol in self.config['market']['symbols']:
            contracts.append((
                con_id, symbol, 'STK', 'SMART', 'USD',
                symbol, symbol, 1, 0.01, 1
            ))
            con_id += 1
        
        # Bulk insert contracts
        if contracts:
            self.connection.executemany("""
                INSERT OR IGNORE INTO contracts (
                    con_id, symbol, security_type, exchange, currency,
                    local_symbol, trading_class, multiplier, min_tick, price_magnifier
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, contracts)
            
            logger.info(f"Created {len(contracts)} default contracts")
    
    def get_account_summary(self, account_id: str) -> Dict:
        """Get account summary"""
        try:
            result = self.connection.execute("""
                SELECT 
                    account_id, net_liquidation, available_funds, buying_power,
                    gross_position_value, cash_balance, realized_pnl, unrealized_pnl,
                    maintenance_margin, initial_margin, base_currency
                FROM accounts
                WHERE account_id = ?
            """, (account_id,)).fetchone()
            
            if not result:
                return {}
            
            return {
                'account_id': result[0],
                'net_liquidation': float(result[1]),
                'available_funds': float(result[2]),
                'buying_power': float(result[3]),
                'gross_position_value': float(result[4]),
                'cash_balance': float(result[5]),
                'realized_pnl': float(result[6]),
                'unrealized_pnl': float(result[7]),
                'maintenance_margin': float(result[8]),
                'initial_margin': float(result[9]),
                'base_currency': result[10]
            }
            
        except Exception as e:
            logger.error(f"Failed to get account summary: {e}")
            return {}
    
    def get_positions(self, account_id: str) -> List[Dict]:
        """Get all positions for an account"""
        try:
            results = self.connection.execute("""
                SELECT 
                    p.con_id, p.symbol, p.security_type, p.currency,
                    p.position, p.avg_cost, p.market_price, p.market_value,
                    p.unrealized_pnl, p.realized_pnl
                FROM positions p
                WHERE p.account_id = ? AND p.position != 0
                ORDER BY p.symbol
            """, (account_id,)).fetchall()
            
            positions = []
            for row in results:
                positions.append({
                    'con_id': row[0],
                    'symbol': row[1],
                    'security_type': row[2],
                    'currency': row[3],
                    'position': float(row[4]),
                    'avg_cost': float(row[5]),
                    'market_price': float(row[6]) if row[6] else 0,
                    'market_value': float(row[7]) if row[7] else 0,
                    'unrealized_pnl': float(row[8]) if row[8] else 0,
                    'realized_pnl': float(row[9]) if row[9] else 0
                })
            
            return positions
            
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return []
    
    def update_position(self, account_id: str, con_id: int, symbol: str,
                       security_type: str, position: float, avg_cost: float):
        """Update or create a position"""
        try:
            self.connection.execute("""
                INSERT OR REPLACE INTO positions (
                    account_id, con_id, symbol, security_type, position, avg_cost
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (account_id, con_id, symbol, security_type, position, avg_cost))
            
            logger.debug(f"Updated position: {symbol} qty={position} for {account_id}")
            
        except Exception as e:
            logger.error(f"Failed to update position: {e}")
            raise
    
    def create_order(self, order_data: Dict) -> int:
        """Create a new order and return order ID"""
        try:
            # Get next order ID
            result = self.connection.execute("SELECT MAX(order_id) FROM orders").fetchone()
            order_id = (result[0] or 0) + 1
            
            # Get next perm ID
            result = self.connection.execute("SELECT MAX(perm_id) FROM orders").fetchone()
            perm_id = (result[0] or 1000) + 1
            
            # Insert order
            self.connection.execute("""
                INSERT INTO orders (
                    order_id, account_id, client_id, perm_id, con_id,
                    symbol, security_type, exchange, action, order_type,
                    total_quantity, remaining_quantity, limit_price, aux_price,
                    time_in_force, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order_id, order_data['account_id'], order_data['client_id'],
                perm_id, order_data['con_id'], order_data['symbol'],
                order_data['security_type'], order_data.get('exchange', 'SMART'),
                order_data['action'], order_data['order_type'],
                order_data['quantity'], order_data['quantity'],
                order_data.get('limit_price'), order_data.get('aux_price'),
                order_data.get('time_in_force', 'DAY'), 'PendingSubmit'
            ))
            
            logger.info(f"Created order {order_id} for {order_data['symbol']}")
            return order_id
            
        except Exception as e:
            logger.error(f"Failed to create order: {e}")
            raise
    
    def update_order_status(self, order_id: int, status: str, filled_qty: float = None,
                           avg_fill_price: float = None):
        """Update order status"""
        try:
            update_fields = ["status = ?", "updated_at = CURRENT_TIMESTAMP"]
            params = [status]
            
            if filled_qty is not None:
                update_fields.append("filled_quantity = ?")
                update_fields.append("remaining_quantity = total_quantity - ?")
                params.extend([filled_qty, filled_qty])
            
            if avg_fill_price is not None:
                update_fields.append("avg_fill_price = ?")
                params.append(avg_fill_price)
            
            if status == 'Filled':
                update_fields.append("filled_at = CURRENT_TIMESTAMP")
            
            params.append(order_id)
            
            query = f"UPDATE orders SET {', '.join(update_fields)} WHERE order_id = ?"
            self.connection.execute(query, params)
            
            logger.debug(f"Updated order {order_id} status to {status}")
            
        except Exception as e:
            logger.error(f"Failed to update order status: {e}")
            raise
    
    def record_execution(self, exec_data: Dict):
        """Record trade execution"""
        try:
            self.connection.execute("""
                INSERT INTO executions (
                    exec_id, order_id, account_id, con_id, symbol,
                    side, shares, price, commission, realized_pnl
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                exec_data['exec_id'], exec_data['order_id'],
                exec_data['account_id'], exec_data['con_id'],
                exec_data['symbol'], exec_data['side'],
                exec_data['shares'], exec_data['price'],
                exec_data.get('commission', 0),
                exec_data.get('realized_pnl', 0)
            ))
            
            logger.info(f"Recorded execution {exec_data['exec_id']}")
            
        except Exception as e:
            logger.error(f"Failed to record execution: {e}")
            raise
    
    def get_open_orders(self, account_id: str) -> List[Dict]:
        """Get all open orders for an account"""
        try:
            results = self.connection.execute("""
                SELECT * FROM open_orders
                WHERE account_id = ?
                ORDER BY created_at DESC
            """, (account_id,)).fetchall()
            
            orders = []
            for row in results:
                orders.append({
                    'order_id': row[0],
                    'account_id': row[1],
                    'symbol': row[2],
                    'action': row[3],
                    'order_type': row[4],
                    'total_quantity': float(row[5]),
                    'filled_quantity': float(row[6]),
                    'remaining_quantity': float(row[7]),
                    'limit_price': float(row[8]) if row[8] else None,
                    'status': row[9],
                    'created_at': row[10]
                })
            
            return orders
            
        except Exception as e:
            logger.error(f"Failed to get open orders: {e}")
            return []
    
    def update_market_data(self, con_id: int, symbol: str, data: Dict):
        """Update market data for a contract"""
        try:
            self.connection.execute("""
                INSERT INTO market_data (
                    con_id, symbol, timestamp, bid_price, bid_size,
                    ask_price, ask_size, last_price, last_size, volume
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                con_id, symbol, datetime.now(),
                data.get('bid'), data.get('bid_size'),
                data.get('ask'), data.get('ask_size'),
                data.get('last'), data.get('last_size'),
                data.get('volume')
            ))
            
        except Exception as e:
            logger.error(f"Failed to update market data: {e}")
    
    def get_contract_by_symbol(self, symbol: str, security_type: str = 'STK') -> Optional[Dict]:
        """Get contract details by symbol"""
        try:
            result = self.connection.execute("""
                SELECT con_id, symbol, security_type, exchange, currency,
                       local_symbol, trading_class, multiplier
                FROM contracts
                WHERE symbol = ? AND security_type = ?
            """, (symbol, security_type)).fetchone()
            
            if result:
                return {
                    'con_id': result[0],
                    'symbol': result[1],
                    'security_type': result[2],
                    'exchange': result[3],
                    'currency': result[4],
                    'local_symbol': result[5],
                    'trading_class': result[6],
                    'multiplier': result[7]
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get contract: {e}")
            return None
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")