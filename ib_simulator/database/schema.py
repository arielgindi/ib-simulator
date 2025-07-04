"""
DuckDB Schema for IB Simulator
Matches Interactive Brokers data structures
"""

SCHEMA_SQL = """
-- Accounts table
CREATE TABLE IF NOT EXISTS accounts (
    account_id VARCHAR PRIMARY KEY,
    username VARCHAR NOT NULL,
    password_hash VARCHAR NOT NULL,
    account_type VARCHAR NOT NULL CHECK (account_type IN ('LIVE', 'PAPER')),
    base_currency VARCHAR DEFAULT 'USD',
    net_liquidation DECIMAL(20,2) NOT NULL,
    available_funds DECIMAL(20,2) NOT NULL,
    buying_power DECIMAL(20,2) NOT NULL,
    gross_position_value DECIMAL(20,2) DEFAULT 0,
    cash_balance DECIMAL(20,2) NOT NULL,
    realized_pnl DECIMAL(20,2) DEFAULT 0,
    unrealized_pnl DECIMAL(20,2) DEFAULT 0,
    maintenance_margin DECIMAL(20,2) DEFAULT 0,
    initial_margin DECIMAL(20,2) DEFAULT 0,
    last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Positions table
CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY,
    account_id VARCHAR NOT NULL REFERENCES accounts(account_id),
    con_id INTEGER NOT NULL,
    symbol VARCHAR NOT NULL,
    security_type VARCHAR NOT NULL CHECK (security_type IN ('STK', 'OPT', 'FUT', 'CASH', 'BOND')),
    currency VARCHAR DEFAULT 'USD',
    position DECIMAL(20,4) NOT NULL,
    avg_cost DECIMAL(20,4) NOT NULL,
    market_price DECIMAL(20,4),
    market_value DECIMAL(20,2),
    unrealized_pnl DECIMAL(20,2),
    realized_pnl DECIMAL(20,2) DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(account_id, con_id)
);

-- Orders table
CREATE TABLE IF NOT EXISTS orders (
    order_id INTEGER PRIMARY KEY,
    account_id VARCHAR NOT NULL REFERENCES accounts(account_id),
    client_id INTEGER NOT NULL,
    perm_id INTEGER UNIQUE NOT NULL,
    parent_id INTEGER,
    con_id INTEGER NOT NULL,
    symbol VARCHAR NOT NULL,
    security_type VARCHAR NOT NULL,
    exchange VARCHAR DEFAULT 'SMART',
    action VARCHAR NOT NULL CHECK (action IN ('BUY', 'SELL')),
    order_type VARCHAR NOT NULL CHECK (order_type IN ('MKT', 'LMT', 'STP', 'STP_LMT', 'MIT', 'LIT')),
    total_quantity DECIMAL(20,4) NOT NULL,
    filled_quantity DECIMAL(20,4) DEFAULT 0,
    remaining_quantity DECIMAL(20,4),
    limit_price DECIMAL(20,4),
    aux_price DECIMAL(20,4),
    avg_fill_price DECIMAL(20,4),
    status VARCHAR NOT NULL DEFAULT 'PendingSubmit',
    time_in_force VARCHAR DEFAULT 'DAY',
    oca_group VARCHAR,
    trail_percent DECIMAL(10,4),
    trail_stop_price DECIMAL(20,4),
    commission DECIMAL(10,4) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    filled_at TIMESTAMP
);

-- Executions table
CREATE TABLE IF NOT EXISTS executions (
    exec_id VARCHAR PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(order_id),
    account_id VARCHAR NOT NULL REFERENCES accounts(account_id),
    con_id INTEGER NOT NULL,
    symbol VARCHAR NOT NULL,
    side VARCHAR NOT NULL CHECK (side IN ('BOT', 'SLD')),
    shares DECIMAL(20,4) NOT NULL,
    price DECIMAL(20,4) NOT NULL,
    commission DECIMAL(10,4) DEFAULT 0,
    realized_pnl DECIMAL(20,2),
    yield DECIMAL(10,4),
    yield_redemption_date DATE,
    exec_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Contracts table
CREATE TABLE IF NOT EXISTS contracts (
    con_id INTEGER PRIMARY KEY,
    symbol VARCHAR NOT NULL,
    security_type VARCHAR NOT NULL,
    exchange VARCHAR DEFAULT 'SMART',
    currency VARCHAR DEFAULT 'USD',
    local_symbol VARCHAR,
    trading_class VARCHAR,
    multiplier INTEGER DEFAULT 1,
    min_tick DECIMAL(10,6) DEFAULT 0.01,
    price_magnifier INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Option contracts table
CREATE TABLE IF NOT EXISTS option_contracts (
    con_id INTEGER PRIMARY KEY REFERENCES contracts(con_id),
    underlying_symbol VARCHAR NOT NULL,
    underlying_con_id INTEGER,
    strike DECIMAL(20,4) NOT NULL,
    expiry DATE NOT NULL,
    right VARCHAR NOT NULL CHECK (right IN ('C', 'P')),
    multiplier INTEGER DEFAULT 100,
    trading_class VARCHAR,
    exercise_style VARCHAR DEFAULT 'AMERICAN'
);

-- Market data table
CREATE TABLE IF NOT EXISTS market_data (
    id INTEGER PRIMARY KEY,
    con_id INTEGER NOT NULL,
    symbol VARCHAR NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    bid_price DECIMAL(20,4),
    bid_size INTEGER,
    ask_price DECIMAL(20,4),
    ask_size INTEGER,
    last_price DECIMAL(20,4),
    last_size INTEGER,
    volume BIGINT,
    open DECIMAL(20,4),
    high DECIMAL(20,4),
    low DECIMAL(20,4),
    close DECIMAL(20,4),
    vwap DECIMAL(20,4),
    UNIQUE(con_id, timestamp)
);

-- Option market data table
CREATE TABLE IF NOT EXISTS option_market_data (
    id INTEGER PRIMARY KEY,
    con_id INTEGER NOT NULL REFERENCES option_contracts(con_id),
    timestamp TIMESTAMP NOT NULL,
    bid_price DECIMAL(20,4),
    bid_size INTEGER,
    ask_price DECIMAL(20,4),
    ask_size INTEGER,
    last_price DECIMAL(20,4),
    last_size INTEGER,
    volume BIGINT,
    open_interest INTEGER,
    implied_volatility DECIMAL(10,6),
    delta DECIMAL(10,6),
    gamma DECIMAL(10,6),
    theta DECIMAL(10,6),
    vega DECIMAL(10,6),
    rho DECIMAL(10,6),
    UNIQUE(con_id, timestamp)
);

-- Historical data table
CREATE TABLE IF NOT EXISTS historical_data (
    id INTEGER PRIMARY KEY,
    con_id INTEGER NOT NULL,
    symbol VARCHAR NOT NULL,
    bar_time TIMESTAMP NOT NULL,
    bar_size VARCHAR NOT NULL,
    open DECIMAL(20,4) NOT NULL,
    high DECIMAL(20,4) NOT NULL,
    low DECIMAL(20,4) NOT NULL,
    close DECIMAL(20,4) NOT NULL,
    volume BIGINT,
    wap DECIMAL(20,4),
    bar_count INTEGER,
    UNIQUE(con_id, bar_time, bar_size)
);

-- Account values history
CREATE TABLE IF NOT EXISTS account_values (
    id INTEGER PRIMARY KEY,
    account_id VARCHAR NOT NULL REFERENCES accounts(account_id),
    timestamp TIMESTAMP NOT NULL,
    net_liquidation DECIMAL(20,2) NOT NULL,
    total_cash_value DECIMAL(20,2) NOT NULL,
    gross_position_value DECIMAL(20,2) NOT NULL,
    unrealized_pnl DECIMAL(20,2),
    realized_pnl DECIMAL(20,2),
    excess_liquidity DECIMAL(20,2),
    maintenance_margin DECIMAL(20,2),
    daily_pnl DECIMAL(20,2)
);

-- Audit log table
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    account_id VARCHAR,
    action_type VARCHAR NOT NULL,
    details TEXT,
    ip_address VARCHAR,
    client_id INTEGER
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_positions_account ON positions(account_id);
CREATE INDEX IF NOT EXISTS idx_orders_account ON orders(account_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_executions_order ON executions(order_id);
CREATE INDEX IF NOT EXISTS idx_market_data_symbol ON market_data(symbol, timestamp);
CREATE INDEX IF NOT EXISTS idx_option_contracts_underlying ON option_contracts(underlying_symbol);
CREATE INDEX IF NOT EXISTS idx_account_values_timestamp ON account_values(account_id, timestamp);
"""

# Views for easier querying
VIEWS_SQL = """
-- Portfolio summary view
CREATE OR REPLACE VIEW portfolio_summary AS
SELECT 
    p.account_id,
    p.symbol,
    p.security_type,
    p.position,
    p.avg_cost,
    p.market_price,
    p.market_value,
    p.unrealized_pnl,
    CASE 
        WHEN p.position > 0 THEN 'LONG'
        WHEN p.position < 0 THEN 'SHORT'
        ELSE 'FLAT'
    END as position_side
FROM positions p
WHERE p.position != 0;

-- Open orders view
CREATE OR REPLACE VIEW open_orders AS
SELECT 
    o.order_id,
    o.account_id,
    o.symbol,
    o.action,
    o.order_type,
    o.total_quantity,
    o.filled_quantity,
    o.remaining_quantity,
    o.limit_price,
    o.status,
    o.created_at
FROM orders o
WHERE o.status NOT IN ('Filled', 'Cancelled', 'Inactive');

-- Today's trades view
CREATE OR REPLACE VIEW todays_trades AS
SELECT 
    e.exec_id,
    e.account_id,
    e.symbol,
    e.side,
    e.shares,
    e.price,
    e.commission,
    e.realized_pnl,
    e.exec_time
FROM executions e
WHERE DATE(e.exec_time) = CURRENT_DATE;
"""