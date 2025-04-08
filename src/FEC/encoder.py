import threading
from enum import Enum
import time
import queue
from src.FEC import LTCoding as LTC
from src.FEC import ReedSolomon2 as RS
from src.util.byte_stream import ByteStream


class CodeType(Enum):
    REED_SOLOMON = 1
    LT_CODING = 2


""" 
Q1: The type of the data to be encoded is bytes, but the input data is a list of bytes.
"""

class Encoder:
    def __init__(self, byte_stream: ByteStream, code_type=CodeType.REED_SOLOMON, input_ratio=0.9, n=100, k=70):
        """
        Initialize the encoder
        
        Parameters:
            byte_stream: The target stream to write encoded data
            code_type: The encoding method, default is Reed-Solomon
            Since we only write the repair symbols to the ByteStream, code_type must be Reed-Solomon.
            input_ratio: Input data utilization ratio
            n: The encoding parameter n (total symbols)
            k: The encoding parameter k (original symbols)
        """
        self.byte_stream = byte_stream
        self.code_type = code_type
        self.n = n
        self.k = k
        
        # Thread control
        self.encode_thread = None
        self.running = False
        
        # Add encoding queue
        self.encode_queue = queue.Queue()
        self.condition = threading.Condition()
        
        # Initialize encoder
        if self.code_type == CodeType.REED_SOLOMON:
            self.codec = RS.ReedSolomon(n, k)
        else:
            self.codec = LTC.LTEncoder(k)
        
        # Automatically start thread
        self.start()
            
    def encode(self, data):
        """
        Add data to the encoding queue
        
        Parameters:
            data: The data to be encoded
            
        Raises:
            ValueError: If ByteStream doesn't have enough space based on input_ratio
        """
        # Check input data size
        if isinstance(data, bytes):
            data_size = len(data)
        else:
            # If data is in list format, estimate size
            data_size = sum(len(packet) if isinstance(packet, (list, bytes)) else 1 for packet in data)
        
        # Check ByteStream available capacity
        available_space = self.byte_stream.available_capacity()
        max_allowed_size = int(available_space * self.input_ratio)
        
        # If input data exceeds allowed size, raise error
        if data_size > max_allowed_size:
            raise ValueError(f"Input data size ({data_size} bytes) exceeds allowed size ({max_allowed_size} bytes), ByteStream space insufficient")
        
        # Add data to encoding queue
        with self.condition:
            self.encode_queue.put(data)
            self.condition.notify()  # Notify waiting thread
    
    def _encoding_loop(self):
        """Main loop of the encoding thread, gets data from the queue and encodes it"""
        while self.running:
            data_to_process = None
            
            # Wait using condition variable
            with self.condition:
                while self.running and self.encode_queue.empty():
                    # Wait for notification, doesn't consume CPU
                    self.condition.wait()
                
                # If still running and queue not empty
                if self.running and not self.encode_queue.empty():
                    data_to_process = self.encode_queue.get()
            
            # If there's data to process
            if data_to_process:
                try:
                    # Split input data into k symbols
                    packets = self._prepare_data(data_to_process)
                    
                    # Encode according to different encoding methods
                    if self.code_type == CodeType.REED_SOLOMON:
                        # Use RS's systematic mode for encoding
                        encoded_data = self.codec.encode_systematic(packets)
                        # Only keep the repair symbols (the last n-k symbols)
                        encoded_data = encoded_data[self.k:]
                    elif self.code_type == CodeType.LT_CODING:
                        # Use LT coding
                        self.codec.set_message_packets(packets)
                        encoded_data = self.codec.encode(range(self.n))
                        encoded_data = [packet[1] for packet in encoded_data]  # Extract data part
                    
                    # Serialize encoded data
                    serialized_data = self._serialize_encoded_data(encoded_data)
                    
                    # Directly write to ByteStream
                    try:
                        # Check if ByteStream has enough space
                        available_space = self.byte_stream.available_capacity()
                        if len(serialized_data) > available_space:
                            # Truncate data to fit available space and report error
                            truncated_data = serialized_data[:available_space] if available_space > 0 else b''
                            print(f"Warning: ByteStream capacity insufficient, discarded {len(serialized_data) - available_space} bytes of data")
                            if available_space > 0:
                                self.byte_stream.push(truncated_data)
                        else:
                            # Push all data to ByteStream
                            self.byte_stream.push(serialized_data)
                    except ValueError as e:
                        print(f"Error writing to ByteStream: {e}")
                    
                    # Mark task as complete
                    self.encode_queue.task_done()
                except Exception as e:
                    print(f"Encoding error: {e}")
                    # Removed sleep to avoid blocking
    
    def _prepare_data(self, data):
        """Split input data into k symbols"""
        if isinstance(data, bytes):
            # Calculate symbol size
            symbol_size = len(data) // self.k
            if symbol_size == 0:
                symbol_size = 1
            
            packets = []
            for i in range(self.k):
                start = i * symbol_size
                end = start + symbol_size if i < self.k - 1 else len(data)
                packets.append(list(data[start:end]))
            return packets
        else:
            # If already in list format
            return data
    
    def _serialize_encoded_data(self, encoded_data):
        """Serialize encoded data into byte stream"""
        result = bytearray()
        for packet in encoded_data:
            # Serialize each symbol into bytes
            if isinstance(packet, list):
                packet_bytes = bytes(packet)
            else:
                packet_bytes = packet
            
            # Add symbol length header
            length = len(packet_bytes)
            result.extend(length.to_bytes(4, byteorder='big'))
            result.extend(packet_bytes)
        
        return bytes(result)
    
    def start(self):
        """Start encoding thread"""
        if not self.running:
            self.running = True
            
            # Start encoding thread
            if self.encode_thread is None or not self.encode_thread.is_alive():
                self.encode_thread = threading.Thread(target=self._encoding_loop)
                self.encode_thread.daemon = True
                self.encode_thread.start()
    
    def stop(self):
        """Stop encoding thread"""
        self.running = False
        
        # Wait for encoding thread to end
        if self.encode_thread and self.encode_thread.is_alive():
            self.encode_thread.join(timeout=1.0)



