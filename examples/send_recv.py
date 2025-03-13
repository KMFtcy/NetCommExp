#!/usr/bin/env python3
import argparse
import sys
import os

# Add project root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.retrans.cmltv_ACK import CAP

def sender():
    socket = CAP()

    socket.bind(("127.0.0.1", 8080))

    socket.connect(("127.0.0.1", 8081))

    # socket.sendto(b"Hello, world!", ("127.0.0.1", 8081))

def receiver():
    socket = CAP()

    socket.bind(("127.0.0.1", 8081))

    socket.listen()

    server, addr = socket.accept()

    print(f"Connection established with {addr}")


def main():
    parser = argparse.ArgumentParser(description="Choose to run as sender or receiver.")
    parser.add_argument('role', choices=['sender', 'receiver'], help="Role to play: sender or receiver")
    args = parser.parse_args()

    if args.role == 'sender':
        print("Running as sender")
        sender()
    elif args.role == 'receiver':
        print("Running as receiver")
        receiver()

if __name__ == "__main__":
    main()