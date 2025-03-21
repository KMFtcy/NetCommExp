class RingBuffer:
    def __init__(self, capacity: int):
        self.buffer = bytearray(capacity)
        self.capacity = capacity
        self.head = 0
        self.tail = 0
        self.size = 0

    def __len__(self) -> int:
        return self.size

    def push(self, data: bytes):
        data_len = len(data)
        if self.size + data_len > self.capacity:
            raise OverflowError("Buffer would overflow")
        
        # If the data needs to wrap around the end of the buffer
        space_to_end = self.capacity - self.tail
        if space_to_end >= data_len:
            # Can copy in one go
            self.buffer[self.tail:self.tail + data_len] = data
            self.tail = (self.tail + data_len) % self.capacity
        else:
            # Need to split the copy
            self.buffer[self.tail:] = data[:space_to_end]
            remaining = data_len - space_to_end
            if remaining > 0:
                self.buffer[:remaining] = data[space_to_end:]
            self.tail = remaining
        
        self.size += data_len

    def pop_front(self) -> int:
        if self.size == 0:
            raise IndexError("Buffer is empty")
        byte = self.buffer[self.head]
        self.head = (self.head + 1) % self.capacity
        self.size -= 1
        return byte

    def pop(self, n: int) -> bytes:
        if n > self.size:
            raise ValueError("Not enough data to pop")
        if n < 0:
            raise ValueError("Pop size must be positive")
        if n == 0:
            return bytes()
            
        result = bytearray(n)
        if self.head + n <= self.capacity:
            # Can copy in one go
            result[:] = self.buffer[self.head:self.head + n]
        else:
            # Need to split the copy
            first_part = self.capacity - self.head
            result[:first_part] = self.buffer[self.head:]
            result[first_part:] = self.buffer[:n - first_part]
            
        self.head = (self.head + n) % self.capacity
        self.size -= n
        return bytes(result)

    def peek(self, n: int) -> bytes:
        if n > self.size:
            raise ValueError("Not enough elements to peek")
        result = bytearray(n)
        if self.head + n <= self.capacity:
            # Can copy in one go
            result[:] = self.buffer[self.head:self.head + n]
        else:
            # Need to split the copy
            first_part = self.capacity - self.head
            result[:first_part] = self.buffer[self.head:]
            result[first_part:] = self.buffer[:n - first_part]
        return bytes(result)

    def get_size(self) -> int:
        """
        Get the current number of bytes stored in the buffer.
        """
        return self.size

    def get_available_space(self) -> int:
        """
        Get the number of bytes that can still be written to the buffer.
        """
        return self.capacity - self.size

    def is_empty(self) -> bool:
        return self.size == 0

    def is_full(self) -> bool:
        return self.size == self.capacity