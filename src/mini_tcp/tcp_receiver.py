class TCPReceiver:
    def __init__(self, reassembler):
        self.reassembler = reassembler
        self.isn = 0
        self.window_size = min(reassembler.window_size(), 65535)
        self.syn_received = False
        self.fin_received = False

    def receive(self, message):
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

        checkpoint = self.reassembler.writer().bytes_pushed() + 1
        absolute_seqno = message.seqno.unwrap(self.isn, checkpoint)
        stream_index = absolute_seqno - 1
        if message.SYN:
            stream_index = 0

        self.reassembler.insert(stream_index, message.payload, message.FIN)

        if message.FIN:
            self.fin_received = True

    def send(self):
        msg = TCPReceiverMessage()

        if self.syn_received:
            absolute_ackno = self.reassembler.writer().bytes_pushed() + 1
            if self.fin_received and self.reassembler.writer().is_closed():
                absolute_ackno += 1
            msg.ackno = Wrap32.wrap(absolute_ackno, self.isn)

        msg.window_size = self.window_size - self.reassembler.reader().bytes_buffered()

        if self.reassembler.has_error():
            msg.RST = True

        return msg

class Reassembler:
    def window_size(self):
        return 65535

    def insert(self, index, payload, fin):
        pass

    def set_error(self):
        pass

    def writer(self):
        return Writer()

    def reader(self):
        return Reader()

    def has_error(self):
        return False

class TCPSenderMessage:
    def __init__(self, seqno, payload, SYN=False, FIN=False, RST=False):
        self.seqno = seqno
        self.payload = payload
        self.SYN = SYN
        self.FIN = FIN
        self.RST = RST

class TCPReceiverMessage:
    def __init__(self):
        self.ackno = None
        self.window_size = 0
        self.RST = False

class Wrap32:
    @staticmethod
    def wrap(value, isn):
        return (value + isn) % (1 << 32)

class Writer:
    def bytes_pushed(self):
        return 0

    def is_closed(self):
        return False

class Reader:
    def bytes_buffered(self):
        return 0 