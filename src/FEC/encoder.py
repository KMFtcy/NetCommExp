import threading
from enum import Enum
import time
import logging
from src.FEC.LTCoding import LTEncoder as LTC
from src.util.byte_stream import ByteStream
import src.FEC.ReedSolomon2 as RS

# add log
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('FEC_Encoder')

class CodeType(Enum):
    REED_SOLOMON = 1
    LT_CODING = 2


""" 
Q1: The type of the data to be encoded is bytes, but the input data is a list of bytes.
"""

class Encoder:
    def __init__(self, byte_stream: ByteStream, code_type=CodeType.REED_SOLOMON, input_ratio=1, n=100, k=70):
        """
        Initialize the encoder
        
        Parameters:
            byte_stream: The target stream to write encoded data
            code_type: The encoding method, default is Reed-Solomon
                Since we only write the repair symbols to the ByteStream, code_type must be Reed-Solomon.
                LT Coding is not supported yet.
            input_ratio: Input data utilization ratio
            n: The encoding parameter n (total symbols)
            k: The encoding parameter k (original symbols)
        """
        self.byte_stream = byte_stream
        self.code_type = code_type
        self.n = n
        self.k = k
        self.input_ratio = input_ratio
        
        # Thread control
        self.encode_thread = None
        self.running = False
        
        # Direct data reference
        self.current_data = None
        self.data_available = False
        self.data_processed = True
        self.condition = threading.Condition()
        
        # Initialize encoder
        if self.code_type == CodeType.REED_SOLOMON:
            self.codec = RS.ReedSolomon(n, k)
            logger.info(f"Initialized Reed-Solomon encoder with n={n}, k={k}")
        else:
            raise ValueError("LT Coding is not supported yet")
            self.codec = LTC.LTEncoder(k)
            logger.info(f"Initialized LT Coding encoder with k={k}")
        
        # Automatically start thread
        self.start()
            
    def encode(self, data):
        """
        Process data for encoding
        
        Parameters:
            data: The data to be encoded
            MUST be multiple of k, otherwise, the data will be truncated to the nearest multiple of k
        Raises:
            ValueError: If ByteStream doesn't have enough space based on input_ratio
        """
        # Check input data size
        if isinstance(data, bytes):
            data_size = len(data)
        else:
            # If data is in list format, estimate size
            data_size = sum(len(packet) if isinstance(packet, (list, bytes)) else 1 for packet in data)
        
        logger.debug(f"Encoding request received for {data_size} bytes of data")
        
        # Check ByteStream available capacity
        available_space = self.byte_stream.available_capacity()
        max_allowed_size = int(available_space * self.input_ratio)
        
        # If input data exceeds allowed size, raise error
        if data_size > max_allowed_size:
            logger.error(f"Input data size ({data_size} bytes) exceeds allowed size ({max_allowed_size} bytes), ByteStream space insufficient")
            raise ValueError(f"Input data size ({data_size} bytes) exceeds allowed size ({max_allowed_size} bytes), ByteStream space insufficient")
        
        # Set the data directly and notify thread
        with self.condition:
            while not self.data_processed and self.running:
                logger.debug("Waiting for previous encoding to complete")
                self.condition.wait()
            
            self.current_data = data
            self.data_available = True
            self.data_processed = False
            self.condition.notify()
            logger.debug(f"Data reference set, notified encoding thread")
    
    def _encoding_loop(self):
        """Main loop of the encoding thread, processes data when available"""
        logger.info("Encoding thread started")
        while self.running:
            data_to_process = None
            
            # Wait using condition variable
            with self.condition:
                while self.running and not self.data_available:
                    # Wait for notification, doesn't consume CPU
                    logger.debug("Encoding thread waiting for data")
                    self.condition.wait()
                
                # If still running and data is available
                if self.running and self.data_available:
                    data_to_process = self.current_data
                    self.data_available = False
                    self._encoding_in_progress = True
                    logger.debug("Retrieved data reference for encoding")
            
            # If there's data to process
            if data_to_process:
                try:
                    logger.info("Starting encoding process")
                    # Split input data into k symbols
                    packets = self._prepare_data(data_to_process)
                    
                    # Encode according to different encoding methods
                    if self.code_type == CodeType.REED_SOLOMON:
                        # Use RS's systematic mode for encoding
                        logger.debug(f"Encoding with Reed-Solomon, {len(packets)} packets")
                        encoded_data = self.codec.encode_systematic(packets)
                        # Only keep the repair symbols (the last n-k symbols)
                        encoded_data = encoded_data[self.k:]
                        logger.debug(f"Generated {len(encoded_data)} repair symbols")
                    elif self.code_type == CodeType.LT_CODING:
                        # Use LT coding
                        logger.debug(f"Encoding with LT Coding, {len(packets)} packets")
                        self.codec.set_message_packets(packets)
                        encoded_data = self.codec.encode(range(self.n))
                        encoded_data = [packet[1] for packet in encoded_data]  # Extract data part
                        logger.debug(f"Generated {len(encoded_data)} encoded symbols")
                    
                    # Serialize encoded data
                    serialized_data = self._serialize_encoded_data(encoded_data)
                    logger.debug(f"Serialized encoded data: {len(serialized_data)} bytes")
                    
                    # Directly write to ByteStream
                    try:
                        # Check if ByteStream has enough space
                        available_space = self.byte_stream.available_capacity()
                        if len(serialized_data) > available_space:
                            # Truncate data to fit available space and report error
                            truncated_data = serialized_data[:available_space] if available_space > 0 else b''
                            logger.warning(f"ByteStream capacity insufficient, discarded {len(serialized_data) - available_space} bytes of data")
                            if available_space > 0:
                                self.byte_stream.push(truncated_data)
                                logger.info(f"Pushed {len(truncated_data)} bytes to ByteStream")
                        else:
                            # Push all data to ByteStream
                            self.byte_stream.push(serialized_data)
                            logger.info(f"Successfully pushed {len(serialized_data)} bytes to ByteStream")
                    except ValueError as e:
                        logger.error(f"Error writing to ByteStream: {e}")
                    
                    # Mark encoding as complete
                    with self.condition:
                        if hasattr(self, '_encoding_in_progress'):
                            delattr(self, '_encoding_in_progress')
                        self.current_data = None
                        self.data_processed = True
                        self.condition.notify_all()
                        
                    logger.info("Encoding process completed")
                except Exception as e:
                    # Mark encoding as complete even if error occurred
                    with self.condition:
                        if hasattr(self, '_encoding_in_progress'):
                            delattr(self, '_encoding_in_progress')
                        self.current_data = None
                        self.data_processed = True
                        self.condition.notify_all()
                        
                    logger.error(f"Encoding error: {str(e)}", exc_info=True)
    
    def _prepare_data(self, data):
        """Split input data into k symbols, padding with zeros if necessary"""
        if isinstance(data, bytes):
            # Calculate symbol size
            symbol_size = len(data) // self.k
            if symbol_size == 0:
                symbol_size = 1
                logger.warning(f"Input data is smaller than k, setting minimum symbol size to 1")
            else:
                logger.debug(f"Symbol size calculated: {symbol_size} bytes")
            
            packets = []
            for i in range(self.k):
                start = i * symbol_size
                end = start + symbol_size if i < self.k - 1 else len(data)
                packet = list(data[start:end])
                
                # Pad with zeros if necessary to ensure all symbols have the same length
                if len(packet) < symbol_size:
                    packet.extend([0] * (symbol_size - len(packet)))
                    logger.warning(f"The input data is not a multiple of k, padding with zeros of length {symbol_size - len(packet)}")
                
                packets.append(packet)
            logger.debug(f"Data prepared: {len(packets)} packets of {symbol_size} bytes each")
            return packets
        else:
            # If already in list format
            logger.debug(f"Data already in list format, using as is: {len(data)} packets")
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
            
            # # Add symbol length header
            # length = len(packet_bytes)
            # result.extend(length.to_bytes(4, byteorder='big'))
            result.extend(packet_bytes)
        
        logger.debug(f"Serialized {len(encoded_data)} packets into {len(result)} bytes")
        return bytes(result)
    
    def start(self):
        """Start encoding thread"""
        if not self.running:
            self.running = True
            logger.info("Starting encoder thread")
            
            # Start encoding thread
            if self.encode_thread is None or not self.encode_thread.is_alive():
                self.encode_thread = threading.Thread(target=self._encoding_loop)
                self.encode_thread.daemon = True
                self.encode_thread.start()
                logger.info("Encoder thread started successfully")
    
    def stop(self):
        """Stop encoding thread"""
        if self.running:
            logger.info("Stopping encoder thread")
            self.running = False
            
            # Wake up the thread if it's waiting
            with self.condition:
                self.condition.notify_all()
            
            # Wait for encoding thread to end
            if self.encode_thread and self.encode_thread.is_alive():
                self.encode_thread.join(timeout=1.0)
                logger.info("Encoder thread stopped")
    
    def wait_for_completion(self, timeout=None):
        """
        Wait for current encoding task to complete
        
        Parameters:
            timeout: Timeout in seconds, None means wait indefinitely
            
        Returns:
            bool: True if encoding completed, False if timeout occurred
        """
        start_time = time.time()
        with self.condition:
            while not self.data_processed and self.running:
                if timeout is not None:
                    remaining_time = timeout - (time.time() - start_time)
                    if remaining_time <= 0:
                        return False
                    self.condition.wait(timeout=remaining_time)
                else:
                    self.condition.wait()
            return self.data_processed
    
    def encode_sync(self, data, timeout=None):
        """
        Synchronously encode data, return after encoding completes
        
        Parameters:
            data: Data to be encoded
            timeout: Timeout in seconds, None means wait indefinitely
            
        Returns:
            bool: True if encoding completed successfully, False if timeout occurred
        """
        # Wait for any previous encoding to complete
        with self.condition:
            while not self.data_processed and self.running:
                self.condition.wait()
                
        # Add data for encoding
        self.encode(data)
        
        # Wait for completion
        return self.wait_for_completion(timeout)



