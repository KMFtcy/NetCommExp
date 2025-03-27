class RingBuffer:
    def __init__(self, size):
        # Round up size to the nearest power of 2
        self.size = self._round_up_power_of_two(size)
        # Create buffer
        self.buffer = bytearray(self.size)
        # Enqueue and dequeue pointers
        self.in_ptr = 0
        self.out_ptr = 0

    def __len__(self):
        return self.in_ptr - self.out_ptr

    def _round_up_power_of_two(self, n):
        """Round up n to the nearest power of 2"""
        if n <= 0:
            return 1
        
        # Find the smallest power of 2 that is greater than or equal to n
        power = 1
        while power < n:
            power *= 2
        return power

    def _mask(self, val):
        """Calculate actual position in buffer, equivalent to modulo operation but more efficient"""
        return val & (self.size - 1)

    def len(self):
        """Return the length of data in buffer"""
        return self.in_ptr - self.out_ptr

    def avail(self):
        """Return available space in buffer"""
        return self.size - (self.in_ptr - self.out_ptr)

    def is_empty(self):
        """Check if buffer is empty"""
        return self.in_ptr == self.out_ptr

    def is_full(self):
        """Check if buffer is full"""
        return self.len() == self.size

    def reset(self):
        """Reset buffer"""
        self.in_ptr = 0
        self.out_ptr = 0

    def push(self, data: bytes) -> int:
        # Raise exception if data exceeds available space
        if len(data) > self.avail():
            raise OverflowError("Buffer overflow")
            
        # Calculate actual write position
        in_pos = self._mask(self.in_ptr)
        
        # Handle data wrap-around case
        # Calculate available space from current position to buffer end
        to_end = min(len(data), self.size - in_pos)
        
        # Copy first part of data (from current position to buffer end)
        self.buffer[in_pos:in_pos + to_end] = data[:to_end]
        
        # If there's remaining data, copy it to the beginning of buffer
        if to_end < len(data):
            self.buffer[:len(data) - to_end] = data[to_end:len(data)]
        
        # Update enqueue pointer
        self.in_ptr += len(data)
        
        return len(data)

    def pop(self, length) -> bytes:
        """Get data from buffer"""
        # Determine readable length
        avail_data = self.len()
        length = min(length, avail_data)
        if length == 0:
            return b''
        
        # Calculate actual read position
        out_pos = self._mask(self.out_ptr)
        
        # Create result buffer
        result = bytearray(length)
        
        # Handle data wrap-around case
        # Calculate readable data amount from current position to buffer end
        to_end = min(length, self.size - out_pos)
        
        # Copy first part of data (from current position to buffer end)
        result[:to_end] = self.buffer[out_pos:out_pos + to_end]
        
        # If more data needed, copy from buffer beginning
        if to_end < length:
            result[to_end:] = self.buffer[:length - to_end]
        
        # Update dequeue pointer
        self.out_ptr += length
        
        return bytes(result)

    def peek(self, length) -> bytes:
        """View data without moving dequeue pointer"""
        # Determine readable length
        avail_data = self.len()
        length = min(length, avail_data)
        if length == 0:
            return b''
        
        # Calculate actual read position
        out_pos = self._mask(self.out_ptr)
        
        # Create result buffer
        result = bytearray(length)
        
        # Handle data wrap-around case
        # Calculate readable data amount from current position to buffer end
        to_end = min(length, self.size - out_pos)
        
        # Copy first part of data (from current position to buffer end)
        result[:to_end] = self.buffer[out_pos:out_pos + to_end]
        
        # If more data needed, copy from buffer beginning
        if to_end < length:
            result[to_end:] = self.buffer[:length - to_end]
        
        return bytes(result)

    def get_available_space(self) -> int:
        """
        Get the number of bytes that can still be written to the buffer.
        """
        return self.size - (self.in_ptr - self.out_ptr)