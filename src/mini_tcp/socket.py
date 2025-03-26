from src.socket import Socket
from src.mini_tcp.tcp_connection import TCPConnection
from src.mini_tcp.tcp_config import TCPConfig
import threading
import time
import asyncio

# MiniTCP socket bridges the os system and our implementation of the TCP connection. Meanwhile, it provides a socket interface for the application to use.

class MiniTCPSocket(Socket):
    def __init__(self, adapter):
        self.adapter = adapter
        self.config = TCPConfig()
        self.tcp_connection = TCPConnection(self.config)
        self.loop_thread = None
        self.running = False
        self.data_available = threading.Event()
        self.dst_address = None

    async def sending_task(self):
        while self.running:
            await asyncio.sleep(1)
            print("Sending...")

    async def receiving_task(self):
        while self.running:
            try:
                message, addr = await asyncio.to_thread(self.adapter.read)
                if message:
                    self.tcp_connection.receive(message, lambda x: self.adapter.sendto(x, addr))
            except Exception as e:
                print(f"Error in receiving task: {e}")
                await asyncio.sleep(1)

    async def ticking_task(self):
        while self.running:
            await asyncio.sleep(self.config.rto / 1000)
            self.tcp_connection.tick(self.config.rto / 1000)

    def start_loop(self):
        """Start the event loop in a separate thread."""
        if not self.running:
            self.running = True
            
            async def run_tasks():
                try:
                    await asyncio.gather(
                        self.sending_task(),
                        self.receiving_task(),
                        self.ticking_task()
                    )
                except Exception as e:
                    print(f"Error in tasks: {e}")
                finally:
                    self.running = False
            
            def run_loop():
                try:
                    asyncio.run(run_tasks())
                except Exception as e:
                    print(f"Error in event loop: {e}")
                finally:
                    self.running = False
            
            self.loop_thread = threading.Thread(target=run_loop)
            self.loop_thread.daemon = True
            self.loop_thread.start()

    def wait_until_closed(self):
        if self.loop_thread:
            self.running = False
            self.loop_thread.join()

    def connect(self, address):
        self.dst_address = address
        self.tcp_connection.push(lambda x: self.adapter.sendto(x, address))
        message, addr = self.adapter.read()
        self.tcp_connection.receive(message, lambda x: self.adapter.sendto(x, addr))
        self.start_loop()
        return

    def listen(self):
        # Don't have to anything yet, minitcp socket can support 1 connection now
        pass

    def accept(self):
        message, addr = self.adapter.read()
        self.dst_address = addr
        self.tcp_connection.receive(message, lambda x: self.adapter.sendto(x, addr))
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
            print(f"Sending {bytes_can_send} bytes to {self.dst_address}")
            outbound_stream.push(data[bytes_sent:bytes_sent + bytes_can_send])
            bytes_sent += bytes_can_send
            self.tcp_connection.push(lambda x: self.adapter.sendto(x, self.dst_address))

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
    