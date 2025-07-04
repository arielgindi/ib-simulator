#!/usr/bin/env python3
"""
Test client for IB Simulator
Demonstrates connecting to the simulator using standard IB API approach
"""

import socket
import struct
import time
import sys
from typing import Optional


class TestIBClient:
    """Simple test client for IB Simulator"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 7497):
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.connected = False
        
    def connect(self):
        """Connect to IB Simulator"""
        try:
            print(f"Connecting to IB Simulator at {self.host}:{self.port}...")
            
            # Create socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            
            # Send initial handshake (IB API protocol)
            # Send "API\0" followed by version range
            handshake = b'API\x00v100..176\x00'
            self.socket.send(handshake)
            
            # Receive server version
            data = self.socket.recv(1024)
            print(f"Received server response: {data}")
            
            # Send START_API message
            self._send_start_api()
            
            self.connected = True
            print("Connected successfully!")
            
            # Start receiving messages
            self._receive_loop()
            
        except Exception as e:
            print(f"Connection failed: {e}")
            
    def _send_start_api(self):
        """Send START_API message"""
        # Message ID 71 = START_API
        # Fields: client_id, optional_capabilities
        fields = [71, 1, ""]  # msg_id, client_id, capabilities
        self._send_message(fields)
        
    def _send_message(self, fields: list):
        """Send a message with IB protocol encoding"""
        # Encode fields
        message = b''
        for field in fields:
            if isinstance(field, int):
                message += str(field).encode('latin-1') + b'\x00'
            else:
                message += str(field).encode('latin-1') + b'\x00'
        
        # Prepend length
        length = len(message)
        full_message = struct.pack('>I', length) + message
        
        print(f"Sending message: {fields}")
        self.socket.send(full_message)
        
    def _receive_loop(self):
        """Receive and display messages"""
        buffer = b''
        
        print("\nListening for messages (press Ctrl+C to stop)...")
        
        try:
            while self.connected:
                # Receive data
                data = self.socket.recv(4096)
                if not data:
                    print("Connection closed by server")
                    break
                
                buffer += data
                
                # Process complete messages
                while len(buffer) >= 4:
                    # Get message length
                    msg_length = struct.unpack('>I', buffer[:4])[0]
                    
                    if len(buffer) < 4 + msg_length:
                        break
                    
                    # Extract message
                    message = buffer[4:4 + msg_length]
                    buffer = buffer[4 + msg_length:]
                    
                    # Decode and display
                    fields = message.split(b'\x00')[:-1]  # Remove trailing empty
                    decoded = [f.decode('latin-1') for f in fields]
                    
                    if decoded:
                        msg_id = decoded[0]
                        print(f"\nReceived message ID {msg_id}: {decoded[1:]}")
                        
        except KeyboardInterrupt:
            print("\nStopping...")
            
    def test_market_data(self):
        """Test market data request"""
        if not self.connected:
            return
            
        print("\nRequesting market data for NVDA...")
        
        # REQ_MKT_DATA = 1
        # Fields: msg_id, req_id, con_id, symbol, sec_type, expiry, strike, 
        #         right, multiplier, exchange, primary_exchange, currency,
        #         local_symbol, trading_class, generic_tick_list, snapshot,
        #         regulatory_snapshot, mkt_data_options
        fields = [
            1,      # msg_id
            100,    # req_id
            0,      # con_id
            "NVDA", # symbol
            "STK",  # sec_type
            "",     # expiry
            0,      # strike
            "",     # right
            1,      # multiplier
            "SMART",# exchange
            "",     # primary_exchange
            "USD",  # currency
            "",     # local_symbol
            "",     # trading_class
            "",     # generic_tick_list
            0,      # snapshot
            0,      # regulatory_snapshot
            ""      # mkt_data_options
        ]
        
        self._send_message(fields)
        
    def test_account_data(self):
        """Test account data request"""
        if not self.connected:
            return
            
        print("\nRequesting account data...")
        
        # REQ_ACCT_DATA = 6
        # Fields: msg_id, subscribe, account_code
        fields = [
            6,   # msg_id
            1,   # subscribe (true)
            ""   # account_code (default)
        ]
        
        self._send_message(fields)
        
    def disconnect(self):
        """Disconnect from server"""
        if self.socket:
            self.socket.close()
            self.connected = False
            print("Disconnected")


def main():
    """Main test function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test client for IB Simulator')
    parser.add_argument('--host', default='127.0.0.1', help='Server host')
    parser.add_argument('--port', type=int, default=7497, help='Server port')
    
    args = parser.parse_args()
    
    # Create client
    client = TestIBClient(args.host, args.port)
    
    # Connect
    client.connect()
    
    # Test features
    time.sleep(1)
    client.test_account_data()
    
    time.sleep(1)
    client.test_market_data()
    
    # Keep running until interrupted
    try:
        while client.connected:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        client.disconnect()


if __name__ == '__main__':
    main()