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
    # adapter = TCPOverUDPAdapter(sock)
    adapter = TCPOverUDPAdapter(sock, debug=debug)
    server_socket = MiniTCPSocket(adapter)
    server_socket.bind((host, port))
    server_socket.listen()
    client_socket, addr = server_socket.accept()
    print(f"Accepted connection from {addr}")


    try:
        print("Waiting for data...")
        while True:
            message = client_socket.recv(1024)
            if message:
                print(f"Received message: {message}, click enter to continue")
            else:
                print("No message received")
            input()
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
        # Send message
        server_addr = (server_host, server_port)
        print("Connecting to server...")
        client_socket.connect(server_addr)
        print(f"Connected to {server_addr}")
        
        # Send the initial message
        print("Sending initial message...")
        client_socket.send(message.encode())
        print(f"Sent message: {message}")
        
        print("\nNow you can type messages to send (press Ctrl+C to exit):")
        while True:
            try:
                # Read input from command line
                user_input = input("> ")
                if user_input.strip():  # Only send non-empty messages
                    client_socket.send(user_input.encode())
                    print(f"Sent message: {user_input}")
            except EOFError:
                break
            
    except KeyboardInterrupt:
        print("\nClient shutting down...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
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