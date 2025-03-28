#!/usr/bin/env python3

import socket
import sys
import os
import argparse
import time

def server(filename, port=5000):
    # Create server socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', port))
    server_socket.listen(1)
    print(f"Server listening on port {port}...")

    # Wait for client connection
    client_socket, addr = server_socket.accept()
    print(f"Connected to client at {addr}")

    print(f"Receiving file as: {filename}")

    # Initialize counters for bandwidth calculation
    total_bytes = 0
    start_time = time.time()

    # Receive file content
    with open(filename, 'wb') as f:
        while True:
            data = client_socket.recv(1024)
            if not data:
                break
            f.write(data)
            total_bytes += len(data)

    end_time = time.time()
    duration = end_time - start_time
    bandwidth = (total_bytes * 8) / duration  # Convert to bits per second
    bandwidth_mbps = bandwidth / (1024 * 1024)  # Convert to Mbps

    print(f"File received successfully")
    print(f"Total bytes received: {total_bytes}")
    print(f"Time taken: {duration:.2f} seconds")
    print(f"Bandwidth: {bandwidth_mbps:.2f} Mbps")
    
    client_socket.close()
    server_socket.close()

def client(filename, host='localhost', port=5000):
    # Create client socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, port))
    print(f"Connected to server at {host}:{port}")

    # Initialize counters for bandwidth calculation
    total_bytes = 0
    start_time = time.time()

    # Send file content
    with open(filename, 'rb') as f:
        while True:
            data = f.read(1024)
            if not data:
                break
            client_socket.send(data)
            total_bytes += len(data)

    end_time = time.time()
    duration = end_time - start_time
    bandwidth = (total_bytes * 8) / duration  # Convert to bits per second
    bandwidth_mbps = bandwidth / (1024 * 1024)  # Convert to Mbps

    print(f"File sent successfully")
    print(f"Total bytes sent: {total_bytes}")
    print(f"Time taken: {duration:.2f} seconds")
    print(f"Bandwidth: {bandwidth_mbps:.2f} Mbps")
    
    client_socket.close()

def main():
    parser = argparse.ArgumentParser(description='File transfer using socket')
    parser.add_argument('filename', help='Name of the file to transfer')
    parser.add_argument('role', choices=['server', 'client'], help='Role of the program (server or client)')
    parser.add_argument('--host', default='localhost', help='Host address for client (default: localhost)')
    parser.add_argument('--port', type=int, default=5000, help='Port number (default: 5000)')

    args = parser.parse_args()

    if args.role == 'client' and not os.path.exists(args.filename):
        print(f"Error: File '{args.filename}' does not exist")
        sys.exit(1)

    if args.role == 'server':
        server(args.filename, args.port)
    else:
        client(args.filename, args.host, args.port)

if __name__ == "__main__":
    main()
