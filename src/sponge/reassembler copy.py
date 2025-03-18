from collections import deque
from src.sponge.byte_stream import ByteStream as stream

# Reassembler is the upstream of ByteStream, receiving segments and reassembling them in order into a byte stream.
# Reassembler contains a buffer with the size of stream's capacity to store the segments that are not in order.
class Reassembler:
    def __init__(self, output: stream):
        self.unass_base = 0  # Index of the first unassembled byte
        self.capacity = output.capacity()  # Buffer capacity
        self.buffer = deque(['\0'] * self.capacity)  # Buffer to store out-of-order data
        self.bitmap = deque([False] * self.capacity)  # Bitmap to track which positions have data
        self.unass_size = 0  # Amount of unassembled but stored data
        self.output_ = output
        self._eof = False  # Flag indicating end of file

    def check_contiguous(self):
        """Check for contiguous data in buffer and push to output stream"""
        tmp = ""
        # Continue processing as long as the front element is set
        while self.bitmap[0]:
            tmp += self.buffer[0]
            self.buffer.popleft()
            self.bitmap.popleft()
            self.buffer.append('\0')
            self.bitmap.append(False)
        
        if len(tmp) > 0:
            # Write to output stream
            self.unass_base += len(tmp)
            self.unass_size -= len(tmp)
            self.output_.push(tmp)

    def insert(self, segment_idx: int, data: str, eof: bool) -> None:
        """
        Insert a segment into the reassembler
        
        Args:
            segment_idx: The starting index of the segment
            data: The data content
            eof: Whether this is the end of the stream
        """
        # Handle EOF flag
        if eof:
            self._eof = True
            
        data_len = len(data)
        # If no data, EOF received, and no unassembled data, end input
        if data_len == 0 and self._eof and self.unass_size == 0:
            self.output_.close()
            return
            
        # Ignore if segment is completely outside the window
        if segment_idx >= self.unass_base + self.capacity:
            return
            
        # If segment starts after current processing position
        if segment_idx >= self.unass_base:
            offset = segment_idx - self.unass_base
            # Calculate actual length that can be stored without exceeding buffer capacity
            real_len = min(data_len, self.capacity - self.output_.bytes_buffered() - offset)
            
            # If we can't store all data, reset EOF flag
            if real_len < data_len:
                self._eof = False
                
            # Store data in buffer
            for i in range(real_len):
                if not self.bitmap[i + offset]:  # If this position doesn't have data yet
                    self.buffer[i + offset] = data[i]
                    self.bitmap[i + offset] = True
                    self.unass_size += 1
        
        # If segment overlaps with current processing position
        elif segment_idx + data_len > self.unass_base:
            offset = self.unass_base - segment_idx
            # Calculate actual length that can be stored
            real_len = min(data_len - offset, self.capacity - self.output_.buffer_size())
            
            # If we can't store all remaining data, reset EOF flag
            if real_len < data_len - offset:
                self._eof = False
                
            # Store data in buffer
            for i in range(real_len):
                if not self.bitmap[i]:  # If this position doesn't have data yet
                    self.buffer[i] = data[i + offset]
                    self.bitmap[i] = True
                    self.unass_size += 1
        
        # Check for contiguous data and output
        self.check_contiguous()
        
        # If EOF received and no unassembled data remains, end input
        if self._eof and self.unass_size == 0:
            self.output_.close()