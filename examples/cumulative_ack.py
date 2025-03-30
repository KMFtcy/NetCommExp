import sys
import os
import argparse

# Add parent directory to system path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.cumulative_ack.socket import Socket
from src.cumulative_ack.message import CumulativeAckProtocolMessage, CumulativeAckSenderMessage, CumulativeAckReceiverMessage, serialize_message
from socket import socket as UDPSocket, AF_INET, SOCK_DGRAM

def test_my_client_send(host, port):
    client = Socket()
    client.bind(('127.0.0.1', 9090))
    client.connect((host, port))
    try:
        while True:
            input_msg = input("Press Enter to send message")
            client.send(input_msg.encode())
    except KeyboardInterrupt:
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
            print(data)
    except KeyboardInterrupt:
        server.close()

    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Cumulative Ack Test')
    parser.add_argument('--test-server-running', action='store_true', help='Test server running')
    parser.add_argument('--client-send', action='store_true', help='Test client send message')
    parser.add_argument('--client-send-my', action='store_true', help='Test client send message')
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