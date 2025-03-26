import socket
from typing import Optional, Tuple
from src.mini_tcp.tcp_message import TCPMessage, TCPSenderMessage, TCPReceiverMessage
from src.mini_tcp.wrapping_intergers import Wrap32
import logging

logging.basicConfig(level=logging.DEBUG)

class TCPOverUDPAdapter:
    def __init__(self, udp_socket: socket.socket, debug: bool = False):
        self.socket = udp_socket
        self.MAX_DATAGRAM_SIZE = 1500 # in bytes
        self.debug = debug
        self.try_to_close = False
        self.udp_recv_on = False # if the udp socket calls recv method, it will not end even if the socket is closed. This flag is used to check if the recv method is on.

    def serialize_tcp_message(self, message: TCPMessage) -> bytes:
        """Serialize TCPMessage into bytes"""
        # Serialize sender message
        sender = message.sender_message
        seqno_bytes = sender.seqno.raw_value.to_bytes(4, 'big') if sender.seqno else b'\x00\x00\x00\x00'
        payload_len = len(sender.payload) if sender.payload else 0
        payload_len_bytes = payload_len.to_bytes(2, 'big')
        flags = (sender.SYN << 2) | (sender.FIN << 1) | sender.RST
        flags_byte = flags.to_bytes(1, 'big')
        
        # Serialize receiver message
        receiver = message.receiver_message
        ackno_bytes = receiver.ackno.raw_value.to_bytes(4, 'big') if receiver.ackno else b'\x00\x00\x00\x00'
        window_size_bytes = receiver.window_size.to_bytes(2, 'big')
        receiver_flags = receiver.RST.to_bytes(1, 'big')

        # Combine all fields
        header = seqno_bytes + ackno_bytes + payload_len_bytes + window_size_bytes + flags_byte + receiver_flags
        return header + (sender.payload if sender.payload else b'')

    def deserialize_tcp_message(self, data: bytes) -> TCPMessage:
        """Deserialize bytes into TCPMessage"""
        # Parse header (14 bytes)
        seqno = int.from_bytes(data[0:4], 'big')
        ackno = int.from_bytes(data[4:8], 'big')
        payload_len = int.from_bytes(data[8:10], 'big')
        window_size = int.from_bytes(data[10:12], 'big')
        sender_flags = data[12]
        receiver_flags = data[13]

        # Parse payload
        payload = data[14:14+payload_len] if payload_len > 0 else b''

        # Create sender message
        sender_message = TCPSenderMessage(
            seqno=Wrap32(seqno),
            payload=payload,
            SYN=bool(sender_flags & 0b100),
            FIN=bool(sender_flags & 0b010),
            RST=bool(sender_flags & 0b001)
        )

        # Create receiver message
        receiver_message = TCPReceiverMessage(
            ackno=Wrap32(ackno) if ackno != 0 else None,
            window_size=window_size,
            RST=bool(receiver_flags)
        )

        return TCPMessage(sender_message, receiver_message)

    def bind(self, address: Tuple[str, int]):
        self.socket.bind(address)

    def close(self):
        self.try_to_close = True
        # if the udp socket calls recv method, send a empty packet to shut down the recv method
        if self.udp_recv_on:
            address = self.socket.getsockname()
            self.socket.sendto(b'', address)
        self.socket.close()


    def sendto(self, message: TCPMessage, address: Tuple[str, int]) -> int:
        if self.debug:
            print(f"Writing message to {address}: {message}")
        """Write TCPMessage to UDP socket"""
        data = self.serialize_tcp_message(message)
        return self.socket.sendto(data, address)

    def read(self) -> Tuple[Optional[TCPMessage], Optional[Tuple[str, int]]]:
        """Read TCPMessage from UDP socket"""
        try:
            if self.try_to_close:
                return None, None
            self.udp_recv_on = True
            data, addr = self.socket.recvfrom(self.MAX_DATAGRAM_SIZE)
            self.udp_recv_on = False
            message = self.deserialize_tcp_message(data)
            if self.debug:
                print(f"Received message from {addr}: {message}")
            return message, addr
        except socket.error:
            return None, None
