from collections import deque
from src.util.byte_stream import ByteStream

class Reassembler:
    def __init__(self, output: ByteStream):
        self.output = output
        self.unass_base = 0  # Index of the first unassembled byte
        # self.unass_size = 0  # Amount of unassembled but stored data
        self.window_size = output.capacity
        # Use deque for efficient operations at both ends
        # self.buffer = deque([0] * self.window_size, maxlen=self.window_size)
        # self.bitmap = deque([False] * self.window_size, maxlen=self.window_size)
        self.buffer = bytearray(self.window_size)
        self.bitmap = bytearray(self.window_size)
        self.eof = False  # Flag indicating end of file

    @property
    def unass_size(self):
        return self.bitmap.count(1)

    def check_contiguous(self):
        # find contiguous segment
        count = 0
        for i in range(self.window_size):
            if not self.bitmap[i]:
                break
            count += 1
        
        if count > 0:
            self.output.push(bytes(self.buffer[:count]))
            self.buffer[:-count] = self.buffer[count:]
            self.buffer[-count:] = b'\x00' * count
            self.bitmap[:-count] = self.bitmap[count:]
            self.bitmap[-count:] = b'\x00' * count
            self.unass_base += count
    
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
            
            # store data in buffer if it is not a empty segment
            if real_len > 0:
                self.buffer[offset:offset+real_len] = data[:real_len]
                self.bitmap[offset:offset+real_len] = b'\x01' * real_len

        # else, if segment overlaps with current processing position
        elif index + data_len > self.unass_base:
            offset = self.unass_base - index
            # calculate actual length can store in window
            real_len = min(data_len - offset, self.output.available_capacity())

            # if we can store all data, set eof
            if real_len >= data_len - offset and eof:
                self.eof = True

            # Ensure buffer and bitmap have enough space
            while len(self.buffer) < self.window_size:
                self.buffer.append(0)
                self.bitmap.append(False)

            # store data in buffer
            for i in range(real_len):
                self.buffer[i] = data[offset + i]
                self.bitmap[i] = True

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
    