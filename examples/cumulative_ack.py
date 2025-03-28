import sys
import os

# Add parent directory to system path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.cumulative_ack.socket import Socket

def main():
    server = Socket()
    server.bind(('localhost', 8080))
    server.listen_and_accept()

    try:
        while True:
            data = server.recv(1024)
            print(data)
    except KeyboardInterrupt:
        server.close()

    

if __name__ == "__main__":
    main()