from src.socket import Socket
from src.mini_tcp.tcp_connection import TCPConnection
from src.mini_tcp.tcp_config import TCPConfig
import threading
import time

# MiniTCP socket bridges the os system and our implementation of the TCP connection. Meanwhile, it provides a socket interface for the application to use.

class MiniTCPSocket(Socket):
    def __init__(self, adapter):
        self.adapter = adapter
        self.config = TCPConfig()
        self.tcp_connection = TCPConnection(self.config)
        self.loop_thread = None
        self.running = False
        self.data_available = threading.Event()

    def start_loop(self):
        def loop():
            self.running = True
            while self.running:
                try:
                    message, _ = self.adapter.read()
                    if message:
                        self.tcp_connection.receive(message)
                        # Set the event when new data is available
                        if self.tcp_connection.inbound_stream.bytes_buffered > 0:
                            self.data_available.set()
                except Exception as e:
                    print(f"Error in loop: {e}")
                    break

        self.loop_thread = threading.Thread(target=loop, daemon=True)
        self.loop_thread.start()

    def wait_until_closed(self):
        if self.loop_thread:
            self.running = False
            self.loop_thread.join()

    def connect(self, address):
        self.tcp_connection.push(lambda x: self.adapter.write(x, address))
        message, addr = self.adapter.read()
        self.tcp_connection.receive(message, lambda x: self.adapter.write(x, addr))
        self.start_loop()
        return

    def listen(self):
        # Don't have to anything yet, minitcp socket can support 1 connection now
        pass

    def accept(self):
        message, addr = self.adapter.read()
        self.tcp_connection.receive(message, lambda x: self.adapter.write(x, addr))
        self.start_loop()  # Start the loop thread after accepting connection
        return self, addr

    def bind(self, address):
        host, port = address
        self.adapter.bind((host, port))

    # send data to the socket
    def send(self, data: bytes):
        outbound_stream = self.tcp_connection.outbound_stream
        bytes_sent = 0
        while bytes_sent <= len(data):
            bytes_can_send = min(outbound_stream.available_capacity(), len(data) - bytes_sent)
            outbound_stream.push(data[bytes_sent:bytes_sent + bytes_can_send])
            bytes_sent += bytes_can_send
            self.tcp_connection.push()

    # receive data from the socket at most size bytes
    def recv(self, size: int):
        inbound_stream = self.tcp_connection.inbound_stream
        while inbound_stream.bytes_buffered() == 0:
            # Wait for data to become available
            self.data_available.wait()
            self.data_available.clear()
        
        bytes_can_receive = min(inbound_stream.bytes_buffered(), size)
        data = inbound_stream.pop(bytes_can_receive)
        # If there's still data in the buffer, keep the event set
        if inbound_stream.bytes_buffered() > 0:
            self.data_available.set()
        return data
    
    # close the socket
    def close(self):
        pass
    
    
    