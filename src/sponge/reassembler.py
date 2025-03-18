from src.sponge.byte_stream import ByteStream

# Reassembler is the upstream of ByteStream
class Reassembler:
    def __init__(self, stream: ByteStream):
        self.unassembled_bytes = {}
        self.first_unassembled = 0
        self.byte_stream = stream

    def insert(self, index: int, data: bytes, eof: bool) -> None:
        if index != self.first_unassembled:
            return

        self.first_unassembled = index + len(data)
        
        # push data to byte stream
        self.byte_stream.push(data)
        
        # if eof, close byte stream
        if eof:
            self.byte_stream.close()