"""
IB Protocol Message Decoder
Decodes messages according to IB TWS API protocol
"""

import struct
import logging
from typing import List, Tuple, Optional, Dict, Any

from .message_ids import IncomingMessageIds

logger = logging.getLogger(__name__)


class MessageDecoder:
    """Decodes messages from IB TWS API protocol"""
    
    def __init__(self, encoding: str = 'latin-1'):
        self.encoding = encoding
    
    def decode_message(self, data: bytes) -> Tuple[Optional[int], List[Any]]:
        """Decode a complete message with length prefix"""
        if len(data) < 4:
            return None, []
        
        # Extract message length (4 bytes, big-endian)
        msg_length = struct.unpack('>I', data[:4])[0]
        
        if len(data) < 4 + msg_length:
            # Incomplete message
            return None, []
        
        # Extract message body
        msg_body = data[4:4 + msg_length]
        
        # Decode fields
        fields = self.decode_fields(msg_body)
        
        if not fields:
            return None, []
        
        # First field is message ID
        msg_id = int(fields[0])
        return msg_id, fields[1:]
    
    def decode_fields(self, data: bytes) -> List[str]:
        """Decode null-terminated fields from message body"""
        fields = []
        current_field = b''
        
        for byte in data:
            if byte == 0:  # Null terminator
                fields.append(current_field.decode(self.encoding))
                current_field = b''
            else:
                current_field += bytes([byte])
        
        # Add last field if no trailing null
        if current_field:
            fields.append(current_field.decode(self.encoding))
        
        return fields
    
    def read_int(self, fields: List[str], index: int) -> Tuple[Optional[int], int]:
        """Read integer field and return (value, next_index)"""
        if index >= len(fields):
            return None, index
        
        try:
            value = int(fields[index]) if fields[index] else None
            return value, index + 1
        except ValueError:
            return None, index + 1
    
    def read_float(self, fields: List[str], index: int) -> Tuple[Optional[float], int]:
        """Read float field and return (value, next_index)"""
        if index >= len(fields):
            return None, index
        
        try:
            value = float(fields[index]) if fields[index] else None
            return value, index + 1
        except ValueError:
            return None, index + 1
    
    def read_str(self, fields: List[str], index: int) -> Tuple[str, int]:
        """Read string field and return (value, next_index)"""
        if index >= len(fields):
            return '', index
        
        return fields[index], index + 1
    
    def read_bool(self, fields: List[str], index: int) -> Tuple[bool, int]:
        """Read boolean field and return (value, next_index)"""
        if index >= len(fields):
            return False, index
        
        value = fields[index] == '1'
        return value, index + 1
    
    # Message parsers
    def parse_req_mkt_data(self, fields: List[str]) -> Dict[str, Any]:
        """Parse market data request"""
        index = 0
        req_id, index = self.read_int(fields, index)
        con_id, index = self.read_int(fields, index)
        symbol, index = self.read_str(fields, index)
        sec_type, index = self.read_str(fields, index)
        expiry, index = self.read_str(fields, index)
        strike, index = self.read_float(fields, index)
        right, index = self.read_str(fields, index)
        multiplier, index = self.read_int(fields, index)
        exchange, index = self.read_str(fields, index)
        primary_exchange, index = self.read_str(fields, index)
        currency, index = self.read_str(fields, index)
        local_symbol, index = self.read_str(fields, index)
        trading_class, index = self.read_str(fields, index)
        
        # Generic tick list
        generic_tick_list, index = self.read_str(fields, index)
        snapshot, index = self.read_bool(fields, index)
        regulatory_snapshot, index = self.read_bool(fields, index)
        mkt_data_options, index = self.read_str(fields, index)
        
        return {
            'req_id': req_id,
            'contract': {
                'con_id': con_id,
                'symbol': symbol,
                'sec_type': sec_type,
                'expiry': expiry,
                'strike': strike,
                'right': right,
                'multiplier': multiplier,
                'exchange': exchange,
                'primary_exchange': primary_exchange,
                'currency': currency,
                'local_symbol': local_symbol,
                'trading_class': trading_class
            },
            'generic_tick_list': generic_tick_list,
            'snapshot': snapshot,
            'regulatory_snapshot': regulatory_snapshot,
            'mkt_data_options': mkt_data_options
        }
    
    def parse_cancel_mkt_data(self, fields: List[str]) -> Dict[str, Any]:
        """Parse cancel market data request"""
        req_id, _ = self.read_int(fields, 0)
        return {'req_id': req_id}
    
    def parse_place_order(self, fields: List[str]) -> Dict[str, Any]:
        """Parse place order request (simplified)"""
        index = 0
        order_id, index = self.read_int(fields, index)
        
        # Contract
        con_id, index = self.read_int(fields, index)
        symbol, index = self.read_str(fields, index)
        sec_type, index = self.read_str(fields, index)
        expiry, index = self.read_str(fields, index)
        strike, index = self.read_float(fields, index)
        right, index = self.read_str(fields, index)
        multiplier, index = self.read_int(fields, index)
        exchange, index = self.read_str(fields, index)
        primary_exchange, index = self.read_str(fields, index)
        currency, index = self.read_str(fields, index)
        local_symbol, index = self.read_str(fields, index)
        trading_class, index = self.read_str(fields, index)
        sec_id_type, index = self.read_str(fields, index)
        sec_id, index = self.read_str(fields, index)
        
        # Order
        action, index = self.read_str(fields, index)
        total_quantity, index = self.read_float(fields, index)
        order_type, index = self.read_str(fields, index)
        limit_price, index = self.read_float(fields, index)
        aux_price, index = self.read_float(fields, index)
        tif, index = self.read_str(fields, index)
        oca_group, index = self.read_str(fields, index)
        account, index = self.read_str(fields, index)
        open_close, index = self.read_str(fields, index)
        origin, index = self.read_int(fields, index)
        order_ref, index = self.read_str(fields, index)
        transmit, index = self.read_bool(fields, index)
        parent_id, index = self.read_int(fields, index)
        
        return {
            'order_id': order_id,
            'contract': {
                'con_id': con_id,
                'symbol': symbol,
                'sec_type': sec_type,
                'expiry': expiry,
                'strike': strike,
                'right': right,
                'multiplier': multiplier,
                'exchange': exchange,
                'primary_exchange': primary_exchange,
                'currency': currency,
                'local_symbol': local_symbol,
                'trading_class': trading_class
            },
            'order': {
                'action': action,
                'total_quantity': total_quantity,
                'order_type': order_type,
                'limit_price': limit_price,
                'aux_price': aux_price,
                'tif': tif,
                'oca_group': oca_group,
                'account': account,
                'open_close': open_close,
                'origin': origin,
                'order_ref': order_ref,
                'transmit': transmit,
                'parent_id': parent_id
            }
        }
    
    def parse_cancel_order(self, fields: List[str]) -> Dict[str, Any]:
        """Parse cancel order request"""
        order_id, _ = self.read_int(fields, 0)
        return {'order_id': order_id}
    
    def parse_req_open_orders(self, fields: List[str]) -> Dict[str, Any]:
        """Parse request open orders"""
        return {}  # No parameters
    
    def parse_req_acct_data(self, fields: List[str]) -> Dict[str, Any]:
        """Parse request account data"""
        index = 0
        subscribe, index = self.read_bool(fields, index)
        account_code, index = self.read_str(fields, index)
        
        return {
            'subscribe': subscribe,
            'account_code': account_code
        }
    
    def parse_req_positions(self, fields: List[str]) -> Dict[str, Any]:
        """Parse request positions"""
        return {}  # No parameters in basic version
    
    def parse_req_positions_multi(self, fields: List[str]) -> Dict[str, Any]:
        """Parse request positions multi"""
        index = 0
        req_id, index = self.read_int(fields, index)
        account, index = self.read_str(fields, index)
        model_code, index = self.read_str(fields, index)
        
        return {
            'req_id': req_id,
            'account': account,
            'model_code': model_code
        }
    
    def parse_req_contract_details(self, fields: List[str]) -> Dict[str, Any]:
        """Parse request contract details"""
        index = 0
        req_id, index = self.read_int(fields, index)
        
        # Contract fields
        con_id, index = self.read_int(fields, index)
        symbol, index = self.read_str(fields, index)
        sec_type, index = self.read_str(fields, index)
        expiry, index = self.read_str(fields, index)
        strike, index = self.read_float(fields, index)
        right, index = self.read_str(fields, index)
        multiplier, index = self.read_int(fields, index)
        exchange, index = self.read_str(fields, index)
        primary_exchange, index = self.read_str(fields, index)
        currency, index = self.read_str(fields, index)
        local_symbol, index = self.read_str(fields, index)
        trading_class, index = self.read_str(fields, index)
        include_expired, index = self.read_bool(fields, index)
        
        return {
            'req_id': req_id,
            'contract': {
                'con_id': con_id,
                'symbol': symbol,
                'sec_type': sec_type,
                'expiry': expiry,
                'strike': strike,
                'right': right,
                'multiplier': multiplier,
                'exchange': exchange,
                'primary_exchange': primary_exchange,
                'currency': currency,
                'local_symbol': local_symbol,
                'trading_class': trading_class
            },
            'include_expired': include_expired
        }
    
    def parse_req_sec_def_opt_params(self, fields: List[str]) -> Dict[str, Any]:
        """Parse request security definition option parameters"""
        index = 0
        req_id, index = self.read_int(fields, index)
        underlying_symbol, index = self.read_str(fields, index)
        fut_fop_exchange, index = self.read_str(fields, index)
        underlying_sec_type, index = self.read_str(fields, index)
        underlying_con_id, index = self.read_int(fields, index)
        
        return {
            'req_id': req_id,
            'underlying_symbol': underlying_symbol,
            'fut_fop_exchange': fut_fop_exchange,
            'underlying_sec_type': underlying_sec_type,
            'underlying_con_id': underlying_con_id
        }
    
    def parse_req_executions(self, fields: List[str]) -> Dict[str, Any]:
        """Parse request executions"""
        index = 0
        req_id, index = self.read_int(fields, index)
        
        # Execution filter
        client_id, index = self.read_int(fields, index)
        account_code, index = self.read_str(fields, index)
        time, index = self.read_str(fields, index)
        symbol, index = self.read_str(fields, index)
        sec_type, index = self.read_str(fields, index)
        exchange, index = self.read_str(fields, index)
        side, index = self.read_str(fields, index)
        
        return {
            'req_id': req_id,
            'filter': {
                'client_id': client_id,
                'account_code': account_code,
                'time': time,
                'symbol': symbol,
                'sec_type': sec_type,
                'exchange': exchange,
                'side': side
            }
        }
    
    def parse_req_ids(self, fields: List[str]) -> Dict[str, Any]:
        """Parse request IDs"""
        num_ids = 1  # Default
        if fields:
            num_ids, _ = self.read_int(fields, 0)
        return {'num_ids': num_ids}
    
    def parse_req_managed_accts(self, fields: List[str]) -> Dict[str, Any]:
        """Parse request managed accounts"""
        return {}  # No parameters
    
    def parse_req_current_time(self, fields: List[str]) -> Dict[str, Any]:
        """Parse request current time"""
        return {}  # No parameters
    
    def parse_req_historical_data(self, fields: List[str]) -> Dict[str, Any]:
        """Parse request historical data"""
        index = 0
        req_id, index = self.read_int(fields, index)
        
        # Contract
        con_id, index = self.read_int(fields, index)
        symbol, index = self.read_str(fields, index)
        sec_type, index = self.read_str(fields, index)
        expiry, index = self.read_str(fields, index)
        strike, index = self.read_float(fields, index)
        right, index = self.read_str(fields, index)
        multiplier, index = self.read_int(fields, index)
        exchange, index = self.read_str(fields, index)
        primary_exchange, index = self.read_str(fields, index)
        currency, index = self.read_str(fields, index)
        local_symbol, index = self.read_str(fields, index)
        trading_class, index = self.read_str(fields, index)
        include_expired, index = self.read_bool(fields, index)
        
        # Historical data parameters
        end_date_time, index = self.read_str(fields, index)
        bar_size_setting, index = self.read_str(fields, index)
        duration_str, index = self.read_str(fields, index)
        use_rth, index = self.read_bool(fields, index)
        what_to_show, index = self.read_str(fields, index)
        format_date, index = self.read_int(fields, index)
        
        return {
            'req_id': req_id,
            'contract': {
                'con_id': con_id,
                'symbol': symbol,
                'sec_type': sec_type,
                'expiry': expiry,
                'strike': strike,
                'right': right,
                'multiplier': multiplier,
                'exchange': exchange,
                'primary_exchange': primary_exchange,
                'currency': currency,
                'local_symbol': local_symbol,
                'trading_class': trading_class
            },
            'end_date_time': end_date_time,
            'bar_size_setting': bar_size_setting,
            'duration_str': duration_str,
            'use_rth': use_rth,
            'what_to_show': what_to_show,
            'format_date': format_date
        }
    
    def parse_start_api(self, fields: List[str]) -> Dict[str, Any]:
        """Parse start API request"""
        index = 0
        client_id, index = self.read_int(fields, index)
        optional_capabilities, index = self.read_str(fields, index)
        
        return {
            'client_id': client_id,
            'optional_capabilities': optional_capabilities
        }
    
    def parse_message(self, msg_id: int, fields: List[str]) -> Dict[str, Any]:
        """Parse message based on ID"""
        parsers = {
            IncomingMessageIds.REQ_MKT_DATA: self.parse_req_mkt_data,
            IncomingMessageIds.CANCEL_MKT_DATA: self.parse_cancel_mkt_data,
            IncomingMessageIds.PLACE_ORDER: self.parse_place_order,
            IncomingMessageIds.CANCEL_ORDER: self.parse_cancel_order,
            IncomingMessageIds.REQ_OPEN_ORDERS: self.parse_req_open_orders,
            IncomingMessageIds.REQ_ACCT_DATA: self.parse_req_acct_data,
            IncomingMessageIds.REQ_POSITIONS: self.parse_req_positions,
            IncomingMessageIds.REQ_POSITIONS_MULTI: self.parse_req_positions_multi,
            IncomingMessageIds.REQ_CONTRACT_DATA: self.parse_req_contract_details,
            IncomingMessageIds.REQ_SEC_DEF_OPT_PARAMS: self.parse_req_sec_def_opt_params,
            IncomingMessageIds.REQ_EXECUTIONS: self.parse_req_executions,
            IncomingMessageIds.REQ_IDS: self.parse_req_ids,
            IncomingMessageIds.REQ_MANAGED_ACCTS: self.parse_req_managed_accts,
            IncomingMessageIds.REQ_CURRENT_TIME: self.parse_req_current_time,
            IncomingMessageIds.REQ_HISTORICAL_DATA: self.parse_req_historical_data,
            IncomingMessageIds.START_API: self.parse_start_api,
        }
        
        parser = parsers.get(msg_id)
        if parser:
            try:
                return parser(fields)
            except Exception as e:
                logger.error(f"Failed to parse message {msg_id}: {e}")
                return {}
        else:
            logger.warning(f"No parser for message ID {msg_id}")
            return {}