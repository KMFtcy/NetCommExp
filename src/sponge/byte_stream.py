# ByteStream is a buffer between network component and user application
class ByteStream:
    def __init__(self, capacity: int):
        self.buffer = bytearray(0)
        self.capacity = capacity
        self.closed = False
        self.error = {}
        self._bytes_pushed = 0
        self._bytes_popped = 0

    # Interfaces for writer
    # push data to stream, but only as much as available capacity allows
    def push(self, data: bytes) -> int:
        if self.is_closed():
            raise ValueError("Stream is closed")
        if len(data) > self.available_capacity():
            raise ValueError("Not enough capacity")
        self._bytes_pushed += len(data)
        self.buffer.extend(data)
        return len(data)

    # signal that the stream is closed and nothing more will be written to it
    def close(self) -> None:
        self.closed = True

    # check if the stream is closed
    def is_closed(self) -> bool:
        return self.closed

    # check how much more bytes can be pushed to the stream
    def available_capacity(self) -> int:
        return self.capacity - len(self.buffer)

    # check how much bytes has been pushed to the stream
    def bytes_pushed(self) -> int:
        return self._bytes_pushed

    # Interfaces for reader
    def peek(self, n: int) -> bytes:
        if self.is_finished():
            raise ValueError("Stream is finished")
        if n > len(self.buffer):
            return self.buffer[-1]
        return self.buffer[:n]

    def pop(self, n: int) -> bytes:
        if self.is_finished():
            raise ValueError("Stream is finished")
        if n > len(self.buffer):
            n = len(self.buffer)
        self._bytes_popped += n
        popped = [self.buffer.pop(0) for _ in range(n)]
        return popped

    # check if the stream is closed and fully popped
    def is_finished(self) -> bool:
        return self.is_closed() and self._bytes_popped == self._bytes_pushed

    # check if the stream has an error
    def has_error(self) -> bool:
        return self.error

    # check how many bytes are currently buffered in the stream
    def bytes_buffered(self) -> int:
        return self._bytes_pushed - self._bytes_popped
    
    # check how many bytes have been popped from the stream
    def bytes_popped(self) -> int:
        return self._bytes_popped
    