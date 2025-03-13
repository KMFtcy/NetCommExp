from enum import IntEnum
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

class CAP(Protocol):
    """CAP protocol implementation"""
    def __init__(self):
        self.listening = False
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        logger.debug(f"CAP socket created")

    def bind(self, address: Tuple[str, int]) -> None:
        """Bind the socket to a specific address and port"""
        self.socket.bind(address)
        logger.debug(f"CAP socket bound to {address}")

    def connect(self, address: Tuple[str, int]) -> None:
        """Connect to a specific address and port"""
        self.socket.connect(address)
        logger.debug(f"Initiating connection to {address}")
        
        # Send SYN
        syn_packet = make_packet(
            seg_type=SegmentType.SYN,
            seq_num=0  # Initial sequence number
        )
        self.socket.send(syn_packet)
        logger.debug(f"Sent SYN packet with seq_num=0")
        
        # Wait for SYN-ACK
        try:
            data = self.socket.recv(1024)  # Adjust buffer size as needed
            syn_ack_segment = parse_packet(data)
            logger.debug(f"Received SYN-ACK packet with seq_num={syn_ack_segment.seq_num}, ack_num={syn_ack_segment.ack_num}")
            
            # Send DataAck to complete handshake
            data_ack_packet = make_packet(
                seg_type=SegmentType.DATA_ACK,
                seq_num=1,  # Increment sequence number
                ack_num=syn_ack_segment.seq_num + 1  # Acknowledge SYN-ACK
            )
            self.socket.send(data_ack_packet)
            logger.debug("Connection established")
            
        except socket.timeout:
            logger.error("Connection timeout while waiting for SYN-ACK")
            raise
        except Exception as e:
            logger.error(f"Connection failed: {str(e)}")
            raise

    def listen(self, backlog: int = 1) -> None:
        """Put the socket in passive mode, waiting for incoming connection requests"""
        self.listening = True

    def accept(self) -> Tuple['CAP', Tuple[str, int]]:
        """Accept an incoming connection request and establish a connection"""
        # Step 1: Wait for a SYN packet
        data, addr = self.socket.recvfrom(1024)  # Adjust buffer size as needed
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
        data, addr = self.socket.recvfrom(1024)  # Adjust buffer size as needed
        data_ack_segment = parse_packet(data)

        if data_ack_segment.type != SegmentType.DATA_ACK:
            logger.error("Expected DataAck packet, but received different type")
            raise ValueError("Invalid packet type received")

        logger.debug(f"Received DataAck packet from {addr} with seq_num={data_ack_segment.seq_num}, ack_num={data_ack_segment.ack_num}")

        # Connection established
        logger.debug("Connection established with client")
        return self, addr

    def sendto(self, data: bytes, address: Tuple[str, int]) -> int:
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
