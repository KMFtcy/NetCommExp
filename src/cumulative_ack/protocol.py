import asyncio
from src.util.byte_stream import ByteStream
from src.cumulative_ack.message import serialize_message, parse_message, CumulativeAckProtocolMessage, CumulativeAckSenderMessage, CumulativeAckReceiverMessage
from collections import deque

BUFFER_SIZE = 65535

class CumulativeAckProtocol:
    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop
        self._transport = None # transport is a socket provided by asyncio, call transport.sendto() to send data

        # Protocol Information
        self.MAX_PACKET_SIZE = 1024

        # Sender Information
        self.seqno = 0
        self.dst_address = None
        self.sender_buffer = ByteStream(BUFFER_SIZE)
        self.last_sent_time = 0
        self.initial_RTO = 1000
        self.RTO = self.initial_RTO
        self.retrans_count = 0
        self.next_seqno = 0
        self.ack_seqno = 0
        self.ackno = 0
        self.ack_received = False
        self.oustanding_segments = deque()
        self.syn_sent = False
        self.syn_received = False
        self.window_size = BUFFER_SIZE

        # Receiver Information
        self.receiver_buffer = ByteStream(BUFFER_SIZE)
        self.last_ackno = 0
        self.event_bytes_received = asyncio.Event()

    @property
    def transport(self):
        return self._transport

    def connection_made(self, transport):
        self._transport = transport
        print("connection made")

    def datagram_received(self, data, addr):
        print(f"Received data {data}")
        # message = parse_message(data)

        # # handle sender process ===
        # receiver_message = message.receiver_message
        # # update ackno
        # if receiver_message.ackno > self.ackno and receiver_message.ackno <= self.ackno + self.window_size and receiver_message.ackno < self.next_seqno:
        #     self.ackno = receiver_message.ackno
        #     # remove oustanding segments
        #     while len(self.oustanding_segments) > 0:
        #         segment = self.oustanding_segments[0]
        #         if segment.seqno + len(segment.payload) <= self.ackno:
        #             self.oustanding_segments.popleft()
        #         else:
        #             break
        #     # reset timer
        #     self.last_sent_time = 0
        # my_sender_message = CumulativeAckSenderMessage(self.seqno)

        # # handle receiver
        # sender_message = message.sender_message
        # if self.receiver_buffer.available_capacity() >= len(sender_message.payload):
        #     bytes_pushed = self.receiver_buffer.push(sender_message.payload)
        #     self.last_ackno = self.last_ackno + bytes_pushed
        #     self.event_bytes_received.set()
        # my_receiver_message = CumulativeAckReceiverMessage(self.next_ackno)

        # # reply
        # message = CumulativeAckProtocolMessage(my_sender_message, my_receiver_message)
        # self._transport.sendto(serialize_message(message), addr)

    def connection_lost(self, exc):
        print("connection lost")

    def error_received(self, exc):
        print(f"Error received: {exc}")

    async def tick(self):
        while True:
            await asyncio.sleep(self.RTO)  # Tick every RTO
            print("ticking")

    def start_tick(self):
        self.tick_task = self.loop.create_task(self.tick())