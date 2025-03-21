from collections import deque
from src.util.byte_stream import ByteStream

class Reassembler:
    def __init__(self, output: ByteStream):
        self.output = output
        self.unass_base = 0  # Index of the first unassembled byte
        self.unass_size = 0  # Amount of unassembled but stored data
        self.window_size = output.capacity
        # Use deque for efficient operations at both ends
        self.buffer = deque([0] * self.window_size, maxlen=self.window_size)
        self.bitmap = deque([False] * self.window_size, maxlen=self.window_size)
        self.eof = False  # Flag indicating end of file

    def check_contiguous(self):
        avail_size = self.window_size - self.unass_size
        # pop first available bytes
        tmp = deque()  # Create an empty deque
        while len(self.bitmap) > 0 and self.bitmap[0] and avail_size > 0:
            tmp.append(self.buffer.popleft())
            self.bitmap.popleft()
            avail_size -= 1
        # push to output
        if len(tmp) > 0:
            self.unass_base += len(tmp)
            self.unass_size -= len(tmp)
            self.output.push(bytes(tmp))
    
    def insert(self, index: int, data: bytes, eof: bool) -> None:
        data_len = len(data)
        # ignore segment that beyond window
        if index >= self.unass_base + self.window_size:
            return
        # If the segment starts after current unassembled base
        if index >= self.unass_base:
            offset = index - self.unass_base
            # calculate actual length can store in window
            real_len = min(data_len, self.output.available_capacity() - offset)

            # if we can store all data, set eof
            if real_len >= data_len and eof:
                self.eof = True

            # Ensure buffer and bitmap have enough space
            while len(self.buffer) < self.window_size:
                self.buffer.append(0)
                self.bitmap.append(False)
                self.unass_size += 1
            
            # store data in buffer
            for i in range(real_len):
                self.buffer[offset + i] = data[i]
                self.bitmap[offset + i] = True
            self.unass_size += real_len

        # else, if segment overlaps with current processing position
        elif index + data_len > self.unass_base:
            offset = self.unass_base - index
            # calculate actual length can store in window
            real_len = min(data_len - offset, self.output.available_capacity())

            # if we can store all data, set eof
            if real_len >= data_len and eof:
                self.eof = True

            # Ensure buffer and bitmap have enough space
            while len(self.buffer) < self.window_size:
                self.buffer.append(0)
                self.bitmap.append(False)
                self.unass_size += 1

            # store data in buffer
            for i in range(real_len):
                self.buffer[i] = data[offset + i]
                self.bitmap[i] = True
            self.unass_size += real_len

        # check contiguous
        self.check_contiguous()

        # if eof and no unassembled data, closed output
        if self.eof and self.unass_size == 0:
            self.output.close()
                
    def count_bytes_pending(self) -> int:
        return self.unass_size

    def output_stream(self) -> ByteStream:
        return self.output

    def has_error(self) -> bool:
        return self.output.has_error()

    def set_error(self) -> None:
        self.output.set_error()
    