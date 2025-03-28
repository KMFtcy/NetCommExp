import asyncio
from src.cumulative_ack.protocol import CumulativeAckProtocol
from enum import Enum
import threading
import time

class SocketRole(Enum):
    SERVER = "server"
    CLIENT = "client"


class Socket:
    def __init__(self):
        self.protocol_loop = asyncio.new_event_loop()
        self.protocol = CumulativeAckProtocol(self.protocol_loop)
        self.src_address = None
        self.dst_address = None
        self.protocol_thread = None
        self._stop_event = threading.Event()

    async def protocol_loop(self):
        self.transport, self.protocol = await self.protocol_loop.create_datagram_endpoint(lambda: self.protocol, local_addr=('localhost', 8080))

        while not self._stop_event.is_set():
            await asyncio.sleep(1)

        self.transport.close()

    def start_loop(self):
        asyncio.set_event_loop(self.protocol_loop)
        self.protocol_loop.run_forever()

    def bind(self, address):
        self.src_address = address

    def connect(self, address):
        self.dst_address = address
        return
    
    def listen_and_accept(self):
        self.protocol_thread = threading.Thread(target=self.start_loop)
        self.protocol_thread.start()
        return self

    def send(self, data: bytes):
        pass
    
    def recv(self, size: int):
        # buffer = self.protocol.receiver_buffer
        # bytes_can_read = min(size, buffer.bytes_buffered())
        # if bytes_can_read == 0:
        #     # Create a future to wait for the event
        #     future = asyncio.run_coroutine_threadsafe(
        #         self.protocol.event_bytes_received.wait(),
        #         self.protocol_loop
        #     )
        #     future.result()  # Wait for the event to complete
        # if buffer.bytes_buffered() == 0:
        #     self.protocol.event_bytes_received.clear()
        # return buffer.pop(bytes_can_read)
        while True:
            time.sleep(10)
        return b"waiting..."

    def close(self):
        self._stop_event.set()
        print("closing")
        self.protocol_thread.join()
        print("closed")