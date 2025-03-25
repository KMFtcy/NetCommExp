from dataclasses import dataclass
from typing import Optional
from src.mini_tcp.wrapping_intergers import Wrap32

@dataclass
class TCPReceiverMessage:
    ackno: Optional[Wrap32] = None
    window_size: int = 0
    RST: bool = False

@dataclass
class TCPSenderMessage:
    seqno: Optional[Wrap32] = None
    payload: Optional[bytes] = None
    SYN: bool = False
    FIN: bool = False
    RST: bool = False

    # How many sequence number in this segment
    def squence_length(self):
        length = len(self.payload) if self.payload else 0
        if self.SYN:
            length += 1
        if self.FIN:
            length += 1
        return length

@dataclass
class TCPMessage:
    sender_message: TCPSenderMessage
    receiver_message: TCPReceiverMessage
