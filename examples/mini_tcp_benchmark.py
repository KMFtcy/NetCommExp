#!/usr/bin/env python3
import socket
import argparse
import sys
import time
import os
from typing import Optional, Tuple

# Add parent directory to system path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.mini_tcp.adapter import TCPOverUDPAdapter
from src.mini_tcp.tcp_message import TCPMessage, TCPSenderMessage, TCPReceiverMessage
from src.mini_tcp.wrapping_intergers import Wrap32
from src.mini_tcp.socket import MiniTCPSocket

def run_server(host: str, port: int, debug: bool):
    """Run the server mode"""
    print(f"Starting server on {host}:{port}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    adapter = TCPOverUDPAdapter(sock, debug=debug)
    server_socket = MiniTCPSocket(adapter)
    server_socket.bind((host, port))
    server_socket.listen()
    client_socket, addr = server_socket.accept()
    print(f"Accepted connection from {addr}")

    try:
        print("Waiting for data...")
        total_bytes = 0
        start_time = time.time()
        
        while True:
            data = client_socket.recv(1024)
            total_bytes += len(data)
            print(f"Received {total_bytes / (1024):.2f} KB in total")
            print(client_socket.tcp_connection.inbound_stream.available_capacity())
            input()
        
        end_time = time.time()
        duration = end_time - start_time
        throughput = total_bytes / duration / (1024*1024)  # MB/s
        
        print("\nTransfer completed!")
        print(f"Total received: {total_bytes / (1024):.2f} KB")
        print(f"Time taken: {duration:.2f} seconds")
        print(f"Throughput: {throughput:.2f} MB/s")
        
    except KeyboardInterrupt:
        print("\nServer shutting down...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client_socket.close()

def run_client(server_host: str, server_port: int, message: str, debug: bool):
    """Run the client mode"""
    print(f"Starting client, connecting to {server_host}:{server_port}")
    
    # Create socket with random port
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    adapter = TCPOverUDPAdapter(sock, debug=debug)
    client_socket = MiniTCPSocket(adapter)
    client_socket.bind(('', 0))  # Bind to random port
    
    try:
        # Connect to server
        server_addr = (server_host, server_port)
        print("Connecting to server...")
        client_socket.connect(server_addr)
        print(f"Connected to {server_addr}")
        
        # Create 10MB of test data
        data_size = 1024*1024 # 1MB in bytes
        chunk_size = 1024  # 1KB chunks
        test_data = b'x' * data_size
        
        print(f"\nStarting to send {data_size/(1024*1024):.2f} MB of data...")
        start_time = time.time()
        bytes_sent = 0
        
        client_socket.send(test_data)
        # while bytes_sent < data_size:
        #     remaining = data_size - bytes_sent
        #     chunk = test_data[bytes_sent:bytes_sent + min(chunk_size, remaining)]
        #     bytes_sent += len(chunk)
            
        #     if bytes_sent % (1024) == 0:  # Print progress every 1MB
        #         print(f"Sent {bytes_sent / (1024):.2f} KB")
        
        end_time = time.time()
        duration = end_time - start_time
        throughput = data_size / duration / (1024*1024)  # MB/s
        
        print("\nTransfer completed!")
        print(f"Total sent: {data_size / (1024*1024):.2f} MB")
        print(f"Time taken: {duration:.5f} seconds")
        print(f"Throughput: {throughput:.2f} MB/s")
            
    except KeyboardInterrupt:
        print("\nClient shutting down...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("Press Enter to close client socket")
        input()
        client_socket.close()

def main():
    parser = argparse.ArgumentParser(description='Mini TCP Example Program')
    parser.add_argument('mode', choices=['server', 'client'], help='Run as server or client')
    parser.add_argument('--host', default='localhost', help='Host address (default: localhost)')
    parser.add_argument('--port', type=int, default=12345, help='Port number (default: 12345)')
    parser.add_argument('--message', default='Hello, Server!', help='Message to send (client mode only)')
    parser.add_argument('--debug', default=False, action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    if args.mode == 'server':
        run_server(args.host, args.port, args.debug)
    else:
        run_client(args.host, args.port, args.message, args.debug)

if __name__ == '__main__':
    main() 