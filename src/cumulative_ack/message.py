from dataclasses import dataclass

@dataclass
class CumulativeAckSenderMessage:
    seqno: int
    payload: bytes
    SYN: bool
    FIN: bool
    # RST: bool

@dataclass
class CumulativeAckReceiverMessage:
    ackno: int
    # window_size: int
    # RST: bool

@dataclass
class CumulativeAckProtocolMessage:
    sender_message: CumulativeAckSenderMessage
    receiver_message: CumulativeAckReceiverMessage

def parse_message(data: bytes) -> CumulativeAckProtocolMessage:
    """
    Parse bytes into CumulativeAckProtocolMessage
    Format:
    - seqno (8 bytes)
    - ackno (8 bytes)
    - control bits (1 byte: SYN, FIN, RST)
    - payload (remaining bytes)
    """
    if len(data) < 17:  # Minimum length: 8 + 8 + 1
        raise ValueError("Message too short")

    # Parse seqno (8 bytes)
    seqno = int.from_bytes(data[0:8], byteorder='big')
    
    # Parse ackno (8 bytes)
    ackno = int.from_bytes(data[8:16], byteorder='big')
    
    # Parse control bits (1 byte)
    control_byte = data[16]
    syn = bool(control_byte & 0x01)
    fin = bool(control_byte & 0x02)
    rst = bool(control_byte & 0x04)
    
    # Get payload (remaining bytes)
    payload = data[17:]

    # Create sender and receiver messages
    sender_msg = CumulativeAckSenderMessage(
        seqno=seqno,
        payload=payload,
        SYN=syn,
        FIN=fin
    )
    
    receiver_msg = CumulativeAckReceiverMessage(
        ackno=ackno,
        # window_size=65535  # Default window size
    )

    return CumulativeAckProtocolMessage(
        sender_message=sender_msg,
        receiver_message=receiver_msg
    )

def serialize_message(msg: CumulativeAckProtocolMessage) -> bytes:
    """
    Serialize CumulativeAckProtocolMessage into bytes
    """
    # Convert seqno to 8 bytes
    seqno_bytes = msg.sender_message.seqno.to_bytes(8, byteorder='big')
    
    # Convert ackno to 8 bytes
    ackno_bytes = msg.receiver_message.ackno.to_bytes(8, byteorder='big')
    
    # Create control byte
    control_byte = 0
    if msg.sender_message.SYN:
        control_byte |= 0x01
    if msg.sender_message.FIN:
        control_byte |= 0x02
    
    # Combine all parts
    return seqno_bytes + ackno_bytes + bytes([control_byte]) + msg.sender_message.payload

