from src.sponge.byte_stream import ByteStream

# Reassembler is the upstream of ByteStream
class Reassembler:
    def __init__(self, capacity: int):
        self.unassembled_bytes = {}
        self.first_unassembled = 0
        self.output = ByteStream(capacity)

    def insert(self, index: int, data: bytes, eof: bool) -> None:
        if index != self.first_unassembled:
            return

        self.first_unassembled = index + len(data)
        
        # push data to byte stream
        self.output.push(data)
        
        # if eof, close byte stream
        if eof:
            self.output.close()