"""
IB Protocol Message Encoder
Encodes messages according to IB TWS API protocol
"""

import struct
import logging
from typing import List, Union, Optional, Any, Dict
from datetime import datetime

from .message_ids import OutgoingMessageIds

logger = logging.getLogger(__name__)


class MessageEncoder:
    """Encodes messages for IB TWS API protocol"""
    
    def __init__(self, encoding: str = 'latin-1'):
        self.encoding = encoding
    
    def encode_fields(self, fields: List[Any]) -> bytes:
        """Encode a list of fields into IB protocol format"""
        message = b''
        
        for field in fields:
            if field is None:
                # Empty field
                message += b'\x00'
            elif isinstance(field, bool):
                # Boolean as 1 or 0
                message += (b'1' if field else b'0') + b'\x00'
            elif isinstance(field, (int, float)):
                # Numbers as strings
                message += str(field).encode(self.encoding) + b'\x00'
            elif isinstance(field, datetime):
                # Datetime as formatted string
                message += field.strftime('%Y%m%d %H:%M:%S').encode(self.encoding) + b'\x00'
            else:
                # Everything else as string
                message += str(field).encode(self.encoding) + b'\x00'
        
        # Prepend message length (4 bytes, big-endian)
        length = len(message)
        return struct.pack('>I', length) + message
    
    def make_message(self, msg_id: int, fields: List[Any]) -> bytes:
        """Create a complete message with ID and fields"""
        all_fields = [msg_id] + fields
        return self.encode_fields(all_fields)
    
    # Connection messages
    def server_version(self, version: int = 176, connection_time: str = None) -> bytes:
        """Send server version on connection"""
        if connection_time is None:
            connection_time = datetime.now().strftime('%Y%m%d %H:%M:%S')
        
        # Special handling for initial handshake - no message ID
        fields = [version, connection_time]
        return self.encode_fields(fields)
    
    def next_valid_id(self, order_id: int) -> bytes:
        """Send next valid order ID"""
        return self.make_message(OutgoingMessageIds.NEXT_VALID_ID, [order_id])
    
    def managed_accounts(self, accounts: str) -> bytes:
        """Send managed accounts list"""
        return self.make_message(OutgoingMessageIds.MANAGED_ACCTS, [accounts])
    
    def error_message(self, req_id: int, error_code: int, error_msg: str) -> bytes:
        """Send error message"""
        return self.make_message(OutgoingMessageIds.ERR_MSG, [
            req_id, error_code, error_msg
        ])
    
    # Market data messages
    def tick_price(self, req_id: int, tick_type: int, price: float, 
                   can_auto_execute: bool = True, past_limit: bool = False) -> bytes:
        """Send tick price update"""
        fields = [req_id, tick_type, price]
        
        # Version 2 fields
        fields.extend([can_auto_execute, past_limit])
        
        return self.make_message(OutgoingMessageIds.TICK_PRICE, fields)
    
    def tick_size(self, req_id: int, tick_type: int, size: int) -> bytes:
        """Send tick size update"""
        return self.make_message(OutgoingMessageIds.TICK_SIZE, [
            req_id, tick_type, size
        ])
    
    def tick_string(self, req_id: int, tick_type: int, value: str) -> bytes:
        """Send tick string update"""
        return self.make_message(OutgoingMessageIds.TICK_STRING, [
            req_id, tick_type, value
        ])
    
    def tick_generic(self, req_id: int, tick_type: int, value: float) -> bytes:
        """Send generic tick update"""
        return self.make_message(OutgoingMessageIds.TICK_GENERIC, [
            req_id, tick_type, value
        ])
    
    def market_data_type(self, req_id: int, market_data_type: int) -> bytes:
        """Send market data type"""
        return self.make_message(OutgoingMessageIds.MARKET_DATA_TYPE, [
            req_id, market_data_type
        ])
    
    # Account messages
    def account_value(self, key: str, value: str, currency: str, account: str) -> bytes:
        """Send account value update"""
        return self.make_message(OutgoingMessageIds.ACCT_VALUE, [
            key, value, currency, account
        ])
    
    def portfolio_value(self, con_id: int, symbol: str, sec_type: str, expiry: str,
                       strike: float, right: str, multiplier: int, primary_exch: str,
                       currency: str, local_symbol: str, trading_class: str,
                       position: float, market_price: float, market_value: float,
                       avg_cost: float, unrealized_pnl: float, realized_pnl: float,
                       account: str) -> bytes:
        """Send portfolio position update"""
        fields = [
            con_id, symbol, sec_type, expiry, strike, right, multiplier,
            primary_exch, currency, local_symbol, trading_class,
            position, market_price, market_value, avg_cost,
            unrealized_pnl, realized_pnl, account
        ]
        return self.make_message(OutgoingMessageIds.PORTFOLIO_VALUE, fields)
    
    def account_update_time(self, timestamp: str) -> bytes:
        """Send account update timestamp"""
        return self.make_message(OutgoingMessageIds.ACCT_UPDATE_TIME, [timestamp])
    
    def account_download_end(self, account: str) -> bytes:
        """Send account download end marker"""
        return self.make_message(OutgoingMessageIds.ACCT_DOWNLOAD_END, [account])
    
    # Position messages
    def position_data(self, account: str, con_id: int, symbol: str, sec_type: str,
                     expiry: str, strike: float, right: str, multiplier: int,
                     exchange: str, currency: str, local_symbol: str, trading_class: str,
                     position: float, avg_cost: float) -> bytes:
        """Send position data"""
        fields = [
            account, con_id, symbol, sec_type, expiry, strike, right,
            multiplier, exchange, currency, local_symbol, trading_class,
            position, avg_cost
        ]
        return self.make_message(OutgoingMessageIds.POSITION_DATA, fields)
    
    def position_end(self) -> bytes:
        """Send position data end marker"""
        return self.make_message(OutgoingMessageIds.POSITION_END, [])
    
    # Order messages
    def open_order(self, order_id: int, con_id: int, symbol: str, sec_type: str,
                   expiry: str, strike: float, right: str, multiplier: int,
                   exchange: str, currency: str, local_symbol: str, trading_class: str,
                   action: str, total_quantity: float, order_type: str,
                   limit_price: float, aux_price: float, tif: str, oca_group: str,
                   account: str, open_close: str, origin: int, order_ref: str,
                   client_id: int, perm_id: int, outside_rth: bool, hidden: bool,
                   discretionary_amt: float, good_after_time: str, fa_group: str,
                   fa_method: str, fa_percentage: str, fa_profile: str,
                   model_code: str, good_till_date: str, rule80a: str,
                   percent_offset: float, settling_firm: str, short_sale_slot: int,
                   designated_location: str, exempt_code: int, auction_strategy: int,
                   starting_price: float, stock_ref_price: float, delta: float,
                   stock_range_lower: float, stock_range_upper: float,
                   display_size: int, block_order: bool, sweep_to_fill: bool,
                   all_or_none: bool, min_qty: int, oca_type: int, etrade_only: bool,
                   firm_quote_only: bool, nbbo_price_cap: float, parent_id: int,
                   trigger_method: int, volatility: float, volatility_type: int,
                   delta_neutral_order_type: str, delta_neutral_aux_price: float,
                   delta_neutral_con_id: int, delta_neutral_settling_firm: str,
                   delta_neutral_clearing_account: str, delta_neutral_clearing_intent: str,
                   delta_neutral_open_close: str, delta_neutral_short_sale: bool,
                   delta_neutral_short_sale_slot: int, delta_neutral_designated_location: str,
                   continuous_update: bool, reference_price_type: int,
                   trail_stop_price: float, trailing_percent: float,
                   basis_points: float, basis_points_type: int, combo_legs_descrip: str,
                   combo_legs_count: int, combo_legs: List, smart_combo_routing_params_count: int,
                   smart_combo_routing_params: List, scale_init_level_size: int,
                   scale_subs_level_size: int, scale_price_increment: float,
                   scale_price_adjust_value: float, scale_price_adjust_interval: int,
                   scale_profit_offset: float, scale_auto_reset: bool,
                   scale_init_position: int, scale_init_fill_qty: int,
                   scale_random_percent: bool, scale_table: str, active_start_time: str,
                   active_stop_time: str, hedge_type: str, hedge_param: str,
                   opt_out_smart_routing: bool, clearing_account: str, clearing_intent: str,
                   not_held: bool, have_delta_neutral_contract: bool,
                   algo_strategy: str, algo_params_count: int, algo_params: List,
                   algo_id: str, what_if: bool, order_misc_options: str,
                   solicited: bool, randomize_size: bool, randomize_price: bool,
                   reference_contract_id: int, pegged_change_amount: float,
                   is_pegged_change_amount_decrease: bool, reference_change_amount: float,
                   reference_exchange_id: str, adjusted_order_type: str,
                   trigger_price: float, adjusted_stop_price: float,
                   adjusted_stop_limit_price: float, adjusted_trailing_amount: float,
                   adjustable_trailing_unit: int, lmt_price_offset: float,
                   conditions_count: int, conditions: List, conditions_cancel_order: bool,
                   conditions_ignore_rth: bool, ext_operator: str, soft_dollar_tier_name: str,
                   soft_dollar_tier_value: str, soft_dollar_tier_display_name: str,
                   cash_qty: float, mifid2_decision_maker: str, mifid2_decision_algo: str,
                   mifid2_execution_trader: str, mifid2_execution_algo: str,
                   dont_use_auto_price_for_hedge: bool, is_oms_container: bool,
                   discretionary_up_to_limit_price: bool, autoCancelDate: str,
                   filledQuantity: float, refFuturesConId: int, autoCancelParent: bool,
                   shareholder: str, imbalanceOnly: bool, routeMarketableToBbo: bool,
                   parentPermId: int, usePriceMgmtAlgo: bool) -> bytes:
        """Send open order (simplified version - full implementation would be very long)"""
        # For simulator, we'll send a simplified version
        fields = [
            order_id, con_id, symbol, sec_type, expiry, strike, right,
            multiplier, exchange, currency, local_symbol, trading_class,
            action, total_quantity, order_type, limit_price, aux_price,
            tif, oca_group, account, open_close, origin, order_ref,
            client_id, perm_id
        ]
        
        # Add remaining fields as empty/default
        fields.extend([
            outside_rth, hidden, discretionary_amt, good_after_time,
            fa_group, fa_method, fa_percentage, fa_profile, model_code,
            good_till_date, rule80a, percent_offset, settling_firm,
            short_sale_slot, designated_location, exempt_code
        ])
        
        return self.make_message(OutgoingMessageIds.OPEN_ORDER, fields)
    
    def order_status(self, order_id: int, status: str, filled: float,
                    remaining: float, avg_fill_price: float, perm_id: int,
                    parent_id: int, last_fill_price: float, client_id: int,
                    why_held: str, mkt_cap_price: float = 0) -> bytes:
        """Send order status update"""
        fields = [
            order_id, status, filled, remaining, avg_fill_price,
            perm_id, parent_id, last_fill_price, client_id, why_held,
            mkt_cap_price
        ]
        return self.make_message(OutgoingMessageIds.ORDER_STATUS, fields)
    
    def open_order_end(self) -> bytes:
        """Send open orders end marker"""
        return self.make_message(OutgoingMessageIds.OPEN_ORDER_END, [])
    
    # Execution messages
    def execution_data(self, req_id: int, order_id: int, con_id: int,
                      symbol: str, sec_type: str, expiry: str, strike: float,
                      right: str, multiplier: int, exchange: str, currency: str,
                      local_symbol: str, trading_class: str, exec_id: str,
                      time: str, account: str, execution_exchange: str,
                      side: str, shares: float, price: float, perm_id: int,
                      client_id: int, liquidation: int, cumulative_qty: float,
                      avg_price: float, order_ref: str, ev_rule: str,
                      ev_multiplier: float, model_code: str, last_liquidity: int) -> bytes:
        """Send execution data"""
        fields = [
            req_id, order_id, con_id, symbol, sec_type, expiry, strike,
            right, multiplier, exchange, currency, local_symbol, trading_class,
            exec_id, time, account, execution_exchange, side, shares, price,
            perm_id, client_id, liquidation, cumulative_qty, avg_price,
            order_ref, ev_rule, ev_multiplier, model_code, last_liquidity
        ]
        return self.make_message(OutgoingMessageIds.EXECUTION_DATA, fields)
    
    def execution_data_end(self, req_id: int) -> bytes:
        """Send execution data end marker"""
        return self.make_message(OutgoingMessageIds.EXECUTION_DATA_END, [req_id])
    
    # Contract messages
    def contract_data(self, req_id: int, symbol: str, sec_type: str, expiry: str,
                     strike: float, right: str, exchange: str, currency: str,
                     local_symbol: str, trading_class: str, con_id: int,
                     min_tick: float, md_size_multiplier: int, multiplier: int,
                     order_types: str, valid_exchanges: str, price_magnifier: int,
                     under_con_id: int, long_name: str, primary_exchange: str,
                     contract_month: str, industry: str, category: str,
                     subcategory: str, time_zone: str, trading_hours: str,
                     liquid_hours: str, ev_rule: str, ev_multiplier: float,
                     sec_id_list_count: int, sec_id_list: List,
                     agg_group: int, under_symbol: str, under_sec_type: str,
                     market_rule_ids: str, real_expiration_date: str,
                     last_trade_time: str, stock_type: str) -> bytes:
        """Send contract details (simplified)"""
        fields = [
            req_id, symbol, sec_type, expiry, strike, right, exchange,
            currency, local_symbol, trading_class, con_id, min_tick,
            md_size_multiplier, multiplier, order_types, valid_exchanges,
            price_magnifier, under_con_id, long_name, primary_exchange
        ]
        
        # Add remaining fields
        fields.extend([
            contract_month, industry, category, subcategory, time_zone,
            trading_hours, liquid_hours, ev_rule, ev_multiplier,
            sec_id_list_count
        ])
        
        return self.make_message(OutgoingMessageIds.CONTRACT_DATA, fields)
    
    def contract_data_end(self, req_id: int) -> bytes:
        """Send contract data end marker"""
        return self.make_message(OutgoingMessageIds.CONTRACT_DATA_END, [req_id])
    
    # Options specific
    def security_definition_option_parameter(self, req_id: int, exchange: str,
                                           underlying_con_id: int, trading_class: str,
                                           multiplier: int, expiration_count: int,
                                           expirations: List[str], strike_count: int,
                                           strikes: List[float]) -> bytes:
        """Send option chain parameters"""
        fields = [
            req_id, exchange, underlying_con_id, trading_class,
            multiplier, expiration_count
        ]
        
        # Add expirations
        fields.extend(expirations)
        fields.append(strike_count)
        
        # Add strikes
        fields.extend(strikes)
        
        return self.make_message(OutgoingMessageIds.SECURITY_DEFINITION_OPTION_PARAMETER, fields)
    
    def security_definition_option_parameter_end(self, req_id: int) -> bytes:
        """Send option parameters end marker"""
        return self.make_message(OutgoingMessageIds.SECURITY_DEFINITION_OPTION_PARAMETER_END, [req_id])
    
    # Historical data
    def historical_data(self, req_id: int, start_date: str, end_date: str,
                       bar_count: int, bars: List[Dict]) -> bytes:
        """Send historical data bars"""
        fields = [req_id, start_date, end_date, bar_count]
        
        # Add each bar
        for bar in bars:
            fields.extend([
                bar['date'], bar['open'], bar['high'], bar['low'],
                bar['close'], bar['volume'], bar['wap'], bar['bar_count']
            ])
        
        return self.make_message(OutgoingMessageIds.HISTORICAL_DATA, fields)
    
    # Current time
    def current_time(self, time: int) -> bytes:
        """Send current server time"""
        return self.make_message(OutgoingMessageIds.CURRENT_TIME, [time])
    
    # Commission report
    def commission_report(self, exec_id: str, commission: float, currency: str,
                         realized_pnl: float, yield_val: float,
                         yield_redemption_date: str) -> bytes:
        """Send commission report"""
        fields = [
            exec_id, commission, currency, realized_pnl,
            yield_val, yield_redemption_date
        ]
        return self.make_message(OutgoingMessageIds.COMMISSION_REPORT, fields)