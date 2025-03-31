import sys
import os
import argparse
import time
import asyncio
# Add parent directory to system path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.cumulative_ack.socket import Socket
from src.cumulative_ack.message import CumulativeAckProtocolMessage, CumulativeAckSenderMessage, CumulativeAckReceiverMessage, serialize_message
from src.cumulative_ack.protocol import CumulativeAckProtocol
from socket import socket as UDPSocket, AF_INET, SOCK_DGRAM

def test_bandwidth_as_client(host, port):
    client = Socket()
    client.bind(('127.0.0.1', 9090))
    client.connect((host, port))
    start_time = time.time()
    packet_count = 100
    packet_size = 1024
    client.send(b'a' * packet_size * packet_count)
    end_time = time.time()
    print(f"Time taken: {end_time - start_time} seconds")
    print(f"Bandwidth: {packet_count * packet_size / (end_time - start_time)} bytes/second")
    print(f"retrans count: {client.protocol.retrans_count}")
    client.close()

def test_bandwidth_as_server(host, port):
    server = Socket()
    server.bind(('127.0.0.1', port))
    server.listen_and_accept()
    while True:
        data = server.recv(1024)
        print(data)

def test_my_client_send(host, port):
    client = Socket()
    client.bind(('127.0.0.1', 9090))
    client.connect((host, port))
    try:
        while True:
            input_msg = input("Press Enter to send message")
            client.send(input_msg.encode())
    except KeyboardInterrupt:
        # client.close()
        pass
    finally:
        client.close()

def test_client_send(message, host, port):
    sender_msg = CumulativeAckSenderMessage(929, message.encode(), False, False)
    receiver_msg = CumulativeAckReceiverMessage(829)
    msg = CumulativeAckProtocolMessage(sender_msg, receiver_msg)
    # send by udp
    client = UDPSocket(AF_INET, SOCK_DGRAM)
    client.sendto(serialize_message(msg), (host, port))
    print("Message sent")

def test_server_running():
    server = Socket()
    server.bind(('127.0.0.1', 8080))
    server.listen_and_accept()
    print("Server started")

    try:
        while True:
            data = server.recv(1024)
            # print(data)
    except KeyboardInterrupt:
        server.close()

def test_protocol_push_bandwidth(host, port):
    # Create event loop and protocol
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    def dummy_send_func(msg):
        pass
    
    def dummy_accept_handler(msg, addr):
        pass
    
    protocol = CumulativeAckProtocol(loop, dummy_send_func, dummy_accept_handler)
    
    # Test parameters
    total_size = 10 * 1024 * 1024  # 10MB
    chunk_size = 1024  # 1KB chunks
    num_chunks = total_size // chunk_size
    
    print(f"Testing protocol push bandwidth with {total_size} bytes in {chunk_size} byte chunks")
    start_time = time.time()
    
    for _ in range(num_chunks):
        protocol.push(b'a' * chunk_size)
    
    # Wait for all data to be acknowledged
    # while len(protocol.oustanding_segments) > 0:
    #     time.sleep(0.1)
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"Time taken: {duration:.2f} seconds")
    print(f"Bandwidth: {total_size / duration / 1024 / 1024:.2f} MB/s")
    print(f"Retransmission count: {protocol.retrans_count}")
    loop.close()

def test_protocol_receive_bandwidth(host, port):
    # Create event loop and protocol
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    def dummy_send_func(msg):
        pass
    
    def dummy_accept_handler(msg, addr):
        pass
    
    protocol = CumulativeAckProtocol(loop, dummy_send_func, dummy_accept_handler)
    
    # Test parameters
    total_size = 10 * 1024 * 1024  # 10MB
    chunk_size = 1024  # 1KB chunks
    num_chunks = total_size // chunk_size
    
    print(f"Testing protocol datagram_received bandwidth with {total_size} bytes in {chunk_size} byte chunks")
    
    # Pre-generate all messages
    print("Generating messages...")
    messages = []
    dummy_addr = ('127.0.0.1', 9090)
    
    for i in range(num_chunks):
        sender_msg = CumulativeAckSenderMessage(i * chunk_size, b'a' * chunk_size, False, False)
        receiver_msg = CumulativeAckReceiverMessage(0)  # Initial ackno is 0
        msg = CumulativeAckProtocolMessage(sender_msg, receiver_msg)
        serialized_msg = serialize_message(msg)
        messages.append((serialized_msg, dummy_addr))
    
    print("Starting bandwidth test...")
    start_time = time.time()
    bytes_received = 0
    
    # Process all messages
    for serialized_msg, addr in messages:
        protocol.datagram_received(serialized_msg, addr)
        bytes_received += chunk_size
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"Time taken: {duration:.2f} seconds")
    print(f"Bandwidth: {total_size / duration / 1024 / 1024:.2f} MB/s")
    loop.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Cumulative Ack Test')
    parser.add_argument('--test-server-running', action='store_true', help='Test server running')
    parser.add_argument('--client-send', action='store_true', help='Test client send message')
    parser.add_argument('--client-send-my', action='store_true', help='Test client send input message')
    parser.add_argument('--bandwidth-client', action='store_true', help='Test bandwidth')
    parser.add_argument('--protocol-push-bandwidth', action='store_true', help='Test protocol push bandwidth')
    parser.add_argument('--protocol-receive-bandwidth', action='store_true', help='Test protocol receive bandwidth')
    parser.add_argument('--message', default='Hello, Server!', help='Message to send (client mode only)')
    parser.add_argument('--host', default='localhost', help='Host address (default: localhost)')
    parser.add_argument('--port', type=int, default=8080, help='Port number (default: 8080)')

    args = parser.parse_args()

    if args.test_server_running:
        test_server_running()
    elif args.client_send:
        test_client_send(args.message, args.host, args.port)
    elif args.client_send_my:
        test_my_client_send(args.host, args.port)
    elif args.bandwidth_client:
        test_bandwidth_as_client(args.host, args.port)
    elif args.protocol_push_bandwidth:
        test_protocol_push_bandwidth(args.host, args.port)
    elif args.protocol_receive_bandwidth:
        test_protocol_receive_bandwidth(args.host, args.port)