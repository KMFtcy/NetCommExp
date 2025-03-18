from src.sponge.byte_stream import ByteStream

# Reassembler is the upstream of ByteStream
class Reassembler:
    def __init__(self, output: ByteStream):
        self.unassembled_bytes = {}
        self.first_unassembled = 0
        self.output = output

    def insert(self, index: int, data: bytes, eof: bool) -> None:
        if index != self.first_unassembled:
            return

        self.first_unassembled = index + len(data)
        
        # push data to byte stream
        self.output.push(data)
        
        # if eof, close byte stream
        if eof:
            self.output.close()