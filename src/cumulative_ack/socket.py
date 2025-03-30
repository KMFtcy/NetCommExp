import asyncio
from src.cumulative_ack.protocol import CumulativeAckProtocol
from src.cumulative_ack.message import CumulativeAckProtocolMessage, serialize_message
from enum import Enum
import threading
import time

class SocketRole(Enum):
    SERVER = "server"
    CLIENT = "client"


class Socket:
    def __init__(self):
        self.protocol_event_loop = asyncio.new_event_loop()
        self.protocol = CumulativeAckProtocol(self.protocol_event_loop, self.send_func, self.accept_handler)
        self.src_address = None
        self.dst_address = None
        self.protocol_thread = None
        self._stop_event = threading.Event()
        self._transport = None

    async def loop_func(self):
        print("start loop")
        new_transport, _ = await self.protocol_event_loop.create_datagram_endpoint(lambda: self.protocol, local_addr=self.src_address)
        self._transport = new_transport
        print(f"listening on {self.src_address}")

        while not self._stop_event.is_set():
            await asyncio.sleep(1)
            # print("transport listening...")

        self._transport.close()

    def send_func(self, message: CumulativeAckProtocolMessage):
        while not self._transport:
            print("waiting for transport")
            time.sleep(1)
        self._transport.sendto(serialize_message(message), self.dst_address)

    def start_loop(self):
        asyncio.set_event_loop(self.protocol_event_loop)
        self.protocol_event_loop.run_until_complete(self.loop_func())

    def bind(self, address):
        self.src_address = address

    def connect(self, address):
        self.dst_address = address
        self.protocol_thread = threading.Thread(target=self.start_loop)
        self.protocol_thread.start()
        return
    
    def listen_and_accept(self):
        self.protocol_thread = threading.Thread(target=self.start_loop)
        self.protocol_thread.start()
        return self

    def accept_handler(self, message: CumulativeAckProtocolMessage, addr):
        if self.dst_address is None:
            self.dst_address = addr

    def send(self, data: bytes):
        self.protocol.push(data)

    def recv(self, size: int):
        buffer = self.protocol.receiver_buffer
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
        while buffer.bytes_buffered() == 0:
            pass
        return buffer.pop(size)

    def close(self):
        self._stop_event.set()
        print("closing")
        self.protocol_thread.join()
        print("closed")