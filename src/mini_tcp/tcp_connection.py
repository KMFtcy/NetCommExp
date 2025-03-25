from src.mini_tcp.tcp_sender import TCPSender
from src.mini_tcp.tcp_receiver import TCPReceiver
from src.mini_tcp.tcp_message import TCPMessage, TCPSenderMessage, TCPReceiverMessage
from src.mini_tcp.tcp_config import TCPConfig
from src.util.byte_stream import ByteStream
from src.mini_tcp.reassembler import Reassembler
from typing import Callable
from src.mini_tcp.wrapping_intergers import Wrap32

def transmit_handler(tcp_connection, sender_msg, original_transmit_func):
    original_transmit_func(TCPMessage(sender_msg, tcp_connection.receiver.send()))
    tcp_connection.need_send = False

# TCPConnection is an instance of a TCP connection. It combines the sender and receiver into a single object and handle their behaviors.
class TCPConnection:
    def __init__(self, config: TCPConfig):
        self.config = config
        self.outbound_stream = ByteStream(config.window_size)
        self.inbound_stream = ByteStream(config.window_size)
        isn = Wrap32(0)
        if config.isn:
            isn = config.isn
        self.sender = TCPSender(self.outbound_stream, isn, config.rto)
        self.receiver = TCPReceiver(Reassembler(self.inbound_stream))
        self.need_send = False # handle when need to send empty message, e.g. when receive SYN+ACK
        self.current_transmit_func = None

    ###########################################
    # Internal Methods                        #
    ###########################################

    def handle_transmit(self, sender_msg: TCPSenderMessage):
        if self.current_transmit_func:
            transmit_handler(self, sender_msg, self.current_transmit_func)

    # push data, use transmit function that can handler sender message and receiver message at once
    def push(self, transmit_func: Callable[[TCPMessage], None]):
        self.current_transmit_func = transmit_func
        self.sender.push(self.handle_transmit)

    def active(self) -> bool:
        # any_error = self.sender.has_error() or self.receiver.has_error()
        # sender_active = self.sender.

        return True


    ###########################################
    # Output Stream Interface (Writing Data)  #
    ###########################################

    # return the number of bytes that can be written to the byte stream
    def remaining_outbound_capacity(self) -> int:
        pass

    # shut down the outbound byte stream, but still allows reading incoming data
    def close_input_stream(self):
        pass

    ###########################################
    # Input Stream Interface (Reading Data)   #
    ###########################################

    # Output interface as reader
    def inbound_stream(self) -> ByteStream:
        pass

    ###########################################
    # Network Event Handlers                  #
    ###########################################

    # called when a new segment has been received from the network
    def receive(self, msg: TCPMessage, transmit_func: Callable[[TCPMessage], None]):

        # If Sender Message occupies a sequence number, make sure to reply
        self.need_send |= msg.sender_message.squence_length() > 0

        # If SenderMessage is a "keep-alive" (with intentionally invalid seqno), make sure to reply
        # (N.B. orthodox TCP rules require a reply on any unacceptable segment.)
        our_ackno = self.receiver.send().ackno
        self.need_send |= (our_ackno is not None) and (msg.sender_message.seqno + 1 == our_ackno)

        # give message to receiver
        self.receiver.receive(msg.sender_message)

        # give message to sender
        self.sender.receive(msg.receiver_message)

        # send message if needed
        self.push(transmit_func)
        if self.need_send:
            transmit_handler(self, self.sender.make_empty_message(), transmit_func)

    
    # called when a timer event occurs periodically
    def tick(self, ms_since_last_tick: int, transmit_func: Callable[[TCPSenderMessage], None]):
        self.sender.tick(ms_since_last_tick, self.make_transmit_func(transmit_func))

    # def segments_out(self) -> int:
    #     pass

    # Is the connection still alive?
    @property
    def alive(self) -> bool:
        pass
