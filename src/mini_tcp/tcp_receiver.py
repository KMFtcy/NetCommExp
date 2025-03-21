from src.mini_tcp.reassembler import Reassembler
from src.mini_tcp.tcp_message import TCPReceiverMessage
from src.mini_tcp.wrapping_intergers import Wrap32

class TCPReceiver:
    def __init__(self, reassembler: Reassembler):
        self.reassembler = reassembler
        self.isn = 0
        self.syn_received = False
        self.fin_received = False
        # window size is at most 65535 (16bits)
        self.window_size = 0;
        if reassembler.window_size < 65535:
            self.window_size = reassembler.window_size
        else:
            self.window_size = 65535

    def receive(self, message: TCPReceiverMessage):
        if message.SYN:
            self.isn = message.seqno
            self.syn_received = True
            if message.FIN:
                self.reassembler.insert(0, "", message.FIN)

        if message.RST:
            self.reassembler.set_error()
            return

        if not self.syn_received:
            return

        checkpoint = self.reassembler.output.bytes_pushed() + 1
        absolute_seqno = message.seqno.unwrap(self.isn, checkpoint)
        stream_index = absolute_seqno - 1
        # if first segment is not SYN, the stream index would be -1, which needs to be converted to 0
        if message.SYN:
            stream_index = 0

        self.reassembler.insert(stream_index, message.payload, message.FIN)

        if message.FIN:
            self.fin_received = True

    def send(self):
        msg = TCPReceiverMessage()

        if self.syn_received:
            absolute_ackno = self.reassembler.output.bytes_pushed() + 1
            if self.fin_received and self.reassembler.output.is_closed():
                absolute_ackno += 1
            msg.ackno = Wrap32.wrap(absolute_ackno, self.isn)

        msg.window_size = self.window_size - self.reassembler.output.bytes_buffered()

        if self.reassembler.has_error():
            msg.RST = True

        return msg