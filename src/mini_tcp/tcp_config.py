from dataclasses import dataclass
from src.mini_tcp.wrapping_intergers import Wrap32

MAX_PAYLOAD_SIZE = 1000
MAX_WINDOW_SIZE = 65535
MAX_RTO = 60000
MIN_RTO = 1000
RTO_SCALE = 4
INITIAL_RTO = 1000
MAX_SEQNO = 2**32 - 1
MAX_RETX_ATTEMPTS = 10
MAX_RETRANSMISSION_TIME = 60000

@dataclass
class TCPConfig:
    payload_size: int = MAX_PAYLOAD_SIZE
    window_size: int = MAX_WINDOW_SIZE
    rto: int = INITIAL_RTO
    rto_scale: int = RTO_SCALE
    initial_rto: int = INITIAL_RTO
    isn: int = 0
