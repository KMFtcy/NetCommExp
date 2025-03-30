import asyncio
from src.util.byte_stream import ByteStream
from src.cumulative_ack.message import serialize_message, parse_message, CumulativeAckProtocolMessage, CumulativeAckSenderMessage, CumulativeAckReceiverMessage
from collections import deque
from typing import Callable
BUFFER_SIZE = 65535

class CumulativeAckProtocol:
    def __init__(self, loop: asyncio.AbstractEventLoop, send_func: Callable[[CumulativeAckProtocolMessage], None], accept_handler: Callable[[CumulativeAckProtocolMessage, tuple[str, int]], None]):
        self.loop = loop
        # transport is a socket provided by asyncio, call transport.sendto() to send data
        self._transport = None
        # The transport detail passed to socket so that socket save the peer address, while protocol only handle control information
        self.send_func = send_func
        # The accept handler handle the syn message for server socket, could be improved
        self.accept_handler = accept_handler
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
        self.loop.create_task(self.tick())
        print("start tick")

    def datagram_received(self, data, addr):
        message = parse_message(data)
        print(f"Received message: {message}")
        self.accept_handler(message, addr)

        # handle sender process ===
        receiver_message = message.receiver_message
        # update ackno
        if receiver_message.ackno > self.ackno:
            self.ackno = receiver_message.ackno
            # remove oustanding segments
            while len(self.oustanding_segments) > 0:
                segment = self.oustanding_segments[0]
                if segment.sender_message.seqno + len(segment.sender_message.payload) <= self.ackno:
                    print(f"Removing acked segment: {segment}")
                    self.oustanding_segments.popleft()
                else:
                    break
            # reset timer
            self.last_sent_time = 0
        my_sender_message = CumulativeAckSenderMessage(self.seqno)
        print(f"Sending sender message: {my_sender_message}")

        # handle receiver
        sender_message = message.sender_message
        if self.receiver_buffer.available_capacity() >= len(sender_message.payload):
            bytes_pushed = self.receiver_buffer.push(sender_message.payload)
            self.last_ackno = self.last_ackno + bytes_pushed
            self.event_bytes_received.set()
        my_receiver_message = CumulativeAckReceiverMessage(self.receiver_buffer.bytes_pushed())
        print(f"Sending receiver message: {my_receiver_message}")

        # reply if payload is not empty
        if len(sender_message.payload) > 0:
            print("replying")
            message = CumulativeAckProtocolMessage(my_sender_message, my_receiver_message)
            self.send_func(message)

    # push data from socket to Protocol, the sending information is determined by the protocol and the sending method is determined by socket
    def push(self, data):
        my_sender_message = CumulativeAckSenderMessage(self.seqno, data, False, False)
        self.seqno += len(data)

        my_receiver_message = CumulativeAckReceiverMessage(self.receiver_buffer.bytes_pushed())

        message = CumulativeAckProtocolMessage(my_sender_message, my_receiver_message)
        self.send_func(message)
        self.oustanding_segments.append(message)

    def connection_lost(self, exc):
        print("connection lost")

    def error_received(self, exc):
        print(f"Error received: {exc}")

    async def tick(self):
        tick_time = self.initial_RTO / 1000
        while True:
            await asyncio.sleep(tick_time)  # Tick every RTO
            if len(self.oustanding_segments) == 0:
                print("no outstanding segments")
                self.reset_timer()
                continue

            print("has outstanding segments")
            self.last_sent_time += tick_time
            if self.last_sent_time >= self.RTO / 1000:
                print("retransmitting")
                self.last_sent_time = 0
                self.retrans_count += 1
                self.RTO *= 2
                self.send_func(self.oustanding_segments[0])

    def reset_timer(self):
        self.last_sent_time = 0
        self.RTO = self.initial_RTO
        self.retrans_count = 0
