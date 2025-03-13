from enum import IntEnum, Enum
from dataclasses import dataclass, field
from src.protocol import Protocol
import socket
import logging
import struct

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)

from typing import Tuple, Any

class SegmentType(IntEnum):
    """Segment types as defined in the protocol"""
    SYN = 0x01      # Connection request
    SYN_ACK = 0x02  # Connection acknowledgment
    DATA = 0x03     # Data segment
    DATA_ACK = 0x04 # Data with acknowledgment
    FIN = 0x05      # Connection termination
    FIN_ACK = 0x06  # Termination acknowledgment

@dataclass
class CAPSegment:
    """Complete CAP segment structure including header and payload
    
    A CAP segment consists of:
    1. Type: Segment type (e.g., DATA, SYN, etc.)
    2. Reserved: Reserved bits
    3. Sequence Number: Sequence number of the segment
    4. Acknowledgment Number: Acknowledgment number
    5. Payload: The actual data being transmitted (optional)
    """
    type: SegmentType = SegmentType.DATA  # 4 bits
    reserved: int = 0                     # 28 bits
    seq_num: int = 0                      # 32 bits
    ack_num: int = 0                      # 32 bits
    payload: bytes = b''                  # Payload

# New enum for connection states
class ConnectionState(Enum):
    CLOSED = 0  # Initial state, connection is closed
    LISTEN = 1  # Receiver waiting for connection request
    SYN_SENT = 2  # Sender has sent connection request
    SYN_RCVD = 3  # Receiver has received and responded to connection request
    ESTABLISHED = 4  # Connection established, data transfer enabled
    FIN_WAIT = 5  # Sender requesting connection termination
    CLOSE_WAIT = 6  # Receiver has received termination request
    TIME_WAIT = 7  # Waiting for all packets to expire

@dataclass
class ConnectionBlock:
    """Records relevant data for a connection"""
    state: ConnectionState = ConnectionState.CLOSED  # Connection state
    local_address: Tuple[str, int] = field(default_factory=lambda: ("", 0))  # Local address
    remote_address: Tuple[str, int] = field(default_factory=lambda: ("", 0))  # Remote address
    seq_num: int = 0  # Sequence number
    ack_num: int = 0  # Acknowledgment number

def make_packet(seg_type: SegmentType, seq_num: int, ack_num: int = 0, payload: bytes = b'') -> bytes:
    """Create a packet from the given parameters
    
    Args:
        seg_type: Type of the segment
        seq_num: Sequence number
        ack_num: Acknowledgment number (default: 0)
        payload: Data payload (default: empty)
        
    Returns:
        Bytes representation of the packet ready for transmission
    """
    # Pack type and reserved into first 32 bits
    first_word = (seg_type << 28) | (0 & 0x0FFFFFFF)  # Reserved is 0
    # Pack header using network byte order (big-endian)
    header = struct.pack('!III', first_word, seq_num, ack_num)
    return header + payload

def parse_packet(data: bytes) -> CAPSegment:
    """Parse received packet data into a CAPSegment
    
    Args:
        data: Raw packet data received from socket
        
    Returns:
        CAPSegment object containing the parsed header and payload
    """
    # Unpack header (first 12 bytes)
    first_word, seq_num, ack_num = struct.unpack('!III', data[:12])
    # Extract type and reserved from first word
    seg_type = SegmentType(first_word >> 28)
    reserved = first_word & 0x0FFFFFFF
    
    # Create segment with header fields merged
    return CAPSegment(
        type=seg_type,
        reserved=reserved,
        seq_num=seq_num,
        ack_num=ack_num,
        payload=data[12:]
    )

"""CAP protocol implementation"""
class CAP(Protocol):
    MTU = 1024

    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Connection Block to record connection data
        self.CB = ConnectionBlock()
        logger.debug(f"CAP socket created")

    def _send(self, data: bytes) -> int:
        """Send data to the socket"""
        return self.socket.sendto(data, self.CB.remote_address)

    def bind(self, address: Tuple[str, int]) -> None:
        """Bind the socket to a specific address and port"""
        self.socket.bind(address)
        logger.debug(f"CAP socket bound to {address}")

    def connect(self, address: Tuple[str, int]) -> None:
        # Set remote address before sending SYN
        self.CB.remote_address = address  # Set remote address
        
        # Send SYN
        syn_packet = make_packet(
            seg_type=SegmentType.SYN,
            seq_num=0  # Initial sequence number
        )
        self._send(syn_packet)
        self.CB.state = ConnectionState.SYN_SENT
        logger.debug(f"Sent SYN packet with seq_num=0")
        
        # Wait for SYN-ACK
        try:
            data = self.socket.recv(1024)  # Adjust buffer size as needed
            syn_ack_segment = parse_packet(data)

            # check if the SYN-ACK packet is received
            if syn_ack_segment.type != SegmentType.SYN_ACK:
                logger.error("Expected SYN-ACK packet, but received different type")
                raise ValueError("Invalid packet type received")

            # Update ConnectionBlock with connection data
            self.CB.state = ConnectionState.ESTABLISHED
            self.CB.local_address = self.socket.getsockname()  # Get local address
            self.CB.seq_num = 1  # Set sequence number
            self.CB.ack_num = syn_ack_segment.seq_num + 1  # Set acknowledgment number
            logger.debug(f"Received SYN-ACK packet with seq_num={syn_ack_segment.seq_num}, ack_num={syn_ack_segment.ack_num}")
                
            # Send DataAck to complete handshake
            data_ack_packet = make_packet(
                seg_type=SegmentType.DATA_ACK,
                seq_num=1,  # Increment sequence number
                ack_num=syn_ack_segment.seq_num + 1  # Acknowledge SYN-ACK
            )
            self._send(data_ack_packet)
            logger.debug("Connection established")

        except socket.timeout:
            logger.error("Connection timeout")
            raise
        except Exception as e:
            logger.error(f"Connection failed: {str(e)}")
            raise

    def listen(self, backlog: int = 1) -> None:
        """Put the socket in passive mode, waiting for incoming connection requests"""
        self.CB.state = ConnectionState.LISTEN

    def accept(self) -> Tuple['CAP', Tuple[str, int]]:
        if self.CB.state != ConnectionState.LISTEN:
            raise ValueError("Socket is not in listening mode")

        """Accept an incoming connection request and establish a connection"""
        # Step 1: Wait for a SYN packet
        data, addr = self.socket.recvfrom(CAP.MTU)  # Adjust buffer size as needed
        syn_segment = parse_packet(data)
        
        if syn_segment.type != SegmentType.SYN:
            logger.error("Expected SYN packet, but received different type")
            raise ValueError("Invalid packet type received")

        logger.debug(f"Received SYN packet from {addr} with seq_num={syn_segment.seq_num}")

        # Step 2: Send SYN-ACK packet
        syn_ack_packet = make_packet(
            seg_type=SegmentType.SYN_ACK,
            seq_num=0,  # Initial sequence number for the server
            ack_num=syn_segment.seq_num + 1  # Acknowledge the client's SYN
        )
        self.socket.sendto(syn_ack_packet, addr)
        logger.debug(f"Sent SYN-ACK packet to {addr} with ack_num={syn_segment.seq_num + 1}")

        # Step 3: Wait for DataAck packet
        data, addr = self.socket.recvfrom(CAP.MTU)  # Adjust buffer size as needed
        data_ack_segment = parse_packet(data)

        if data_ack_segment.type != SegmentType.DATA_ACK:
            logger.error("Expected DataAck packet, but received different type")
            raise ValueError("Invalid packet type received")

        logger.debug(f"Received DataAck packet from {addr} with seq_num={data_ack_segment.seq_num}, ack_num={data_ack_segment.ack_num}")

        # Update ConnectionBlock with connection data
        self.CB.state = ConnectionState.ESTABLISHED
        self.CB.local_address = self.socket.getsockname()  # Get local address
        self.CB.remote_address = addr  # Set remote address
        self.CB.seq_num = 0  # Set sequence number for server
        self.CB.ack_num = data_ack_segment.seq_num + 1  # Set acknowledgment number

        # Connection established
        logger.debug("Connection established with client")
        return self, addr

    def send(self, data: bytes) -> int:
        """Send data to a specific address and port"""
        pass

    def recv(self, bufsize: int) -> bytes:
        """Receive data from the socket"""
        pass

    def close(self) -> None:
        """Close the socket"""
        self.socket.close()
        pass

    def setsockopt(self, level: int, optname: str, value: Any) -> None:
        """Set socket options"""
        pass

    def getsockopt(self, level: int, optname: str) -> Any:
        """Get socket options"""
        pass
