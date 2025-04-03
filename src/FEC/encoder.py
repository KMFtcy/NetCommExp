import threading
from enum import Enum
import time
import queue
from . import LTCoding as LTC
from . import ReedSolomon2 as RS
from src.util.ringbuffer import RingBuffer
from src.util.byte_stream import ByteStream


class CodeType(Enum):
    REED_SOLOMON = 1
    LT_CODING = 2


""" 
Q1: The type of the data to be encoded is bytes, but the input data is a list of bytes.
Q2: There are 2 threads, one is encoding thread, the other is transmission thread. 
    The tranmission thread check the buffer and write the data to the ByteStream every 0.01 second.
    Is there any problem with the design?
"""

class Encoder:
    def __init__(self, byte_stream: ByteStream, code_type=CodeType.REED_SOLOMON, buffer_size=1024*1024, n=100, k=70):
        """
        Initialize the encoder
        
        Parameters:
            byte_stream: The target stream to write encoded data
            code_type: The encoding method, default is Reed-Solomon
            buffer_size: The size of the internal buffer
            n: The encoding parameter n (total symbols)
            k: The encoding parameter k (original symbols)
        """
        self.byte_stream = byte_stream
        self.code_type = code_type
        self.buffer = RingBuffer(buffer_size)
        self.n = n
        self.k = k
        
        # Thread control
        self.encode_thread = None
        self.transmit_thread = None
        self.running = False
        
        # Add encoding queue
        self.encode_queue = queue.Queue()
        
        # Initialize encoder
        if self.code_type == CodeType.REED_SOLOMON:
            self.codec = RS.ReedSolomon(n, k)
        else:
            self.codec = LTC.LTEncoder(k)
        
        # Automatically start threads
        self.start()
            
    def encode(self, data):
        """
        Add data to the encoding queue
        
        Parameters:
            data: The data to be encoded
        """
        # Add data to queue, encoding thread will process it
        self.encode_queue.put(data)
    
    def _encoding_loop(self):
        """Main loop of the encoding thread, gets data from the queue and encodes it"""
        while self.running:
            try:
                # Get data in non-blocking way, check running state after timeout
                try:
                    data = self.encode_queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                
                # Split input data into k symbols
                packets = self._prepare_data(data)
                
                # Encode according to different encoding methods
                if self.code_type == CodeType.REED_SOLOMON:
                    # Use RS's systematic mode for encoding
                    encoded_data = self.codec.encode_systematic(packets)
                elif self.code_type == CodeType.LT_CODING:
                    # Use LT coding
                    self.codec.set_message_packets(packets)
                    encoded_data = self.codec.encode(range(self.n))
                    encoded_data = [packet[1] for packet in encoded_data]  # Extract data part
                
                # Serialize encoded data and store in buffer
                serialized_data = self._serialize_encoded_data(encoded_data)
                self._store_to_buffer(serialized_data)
                
                # Mark task as complete
                self.encode_queue.task_done()
            except Exception as e:
                print(f"Encoding error: {e}")
                time.sleep(0.01)
    
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
    
    def _store_to_buffer(self, data):
        """Store the data to the internal buffer"""
        if len(data) > self.buffer.get_available_space():
            raise ValueError("Encoded data exceeds the buffer capacity")
        self.buffer.push(data)
    
    def start(self):
        """Start encoding and transmission threads"""
        if not self.running:
            self.running = True
            
            # Start encoding thread
            if self.encode_thread is None or not self.encode_thread.is_alive():
                self.encode_thread = threading.Thread(target=self._encoding_loop)
                self.encode_thread.daemon = True
                self.encode_thread.start()
            
            # Start transmission thread
            if self.transmit_thread is None or not self.transmit_thread.is_alive():
                self.transmit_thread = threading.Thread(target=self._transmission_loop)
                self.transmit_thread.daemon = True
                self.transmit_thread.start()
    
    def stop(self):
        """Stop all threads"""
        self.running = False
        
        # Wait for encoding thread to end
        if self.encode_thread and self.encode_thread.is_alive():
            self.encode_thread.join(timeout=1.0)
        
        # Wait for transmission thread to end
        if self.transmit_thread and self.transmit_thread.is_alive():
            self.transmit_thread.join(timeout=1.0)
    
    # Compatible with old interface
    def start_transmission(self):
        """Start the transmission thread (backwards compatibility)"""
        self.start()
    
    def stop_transmission(self):
        """Stop the transmission thread (backwards compatibility)"""
        self.stop()
    
    def _transmission_loop(self):
        """The transmission loop, write the data to the ByteStream"""
        while self.running:
            # Check if buffer has data
            if not self.buffer.is_empty():
                # Check if ByteStream has enough space
                available_space = self.byte_stream.available_capacity()
                if available_space > 0:
                    # Determine how much data to transmit
                    data_size = min(available_space, self.buffer.get_size())
                    # Get data from buffer
                    data = self.buffer.pop(data_size)
                    # Write to ByteStream
                    try:
                        self.byte_stream.push(data)
                    except ValueError as e:
                        # Handle cases where stream is closed or not enough capacity
                        print(f"Transmission error: {e}")
                        time.sleep(0.01)  # Avoid excessive CPU usage
                else:
                    # ByteStream has no enough space, wait
                    time.sleep(0.01)
            else:
                # Buffer is empty, wait
                time.sleep(0.01)



