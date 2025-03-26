import unittest
from src.mini_tcp.tcp_receiver import TCPReceiver
from src.mini_tcp.tcp_message import TCPSenderMessage
from src.mini_tcp.wrapping_intergers import Wrap32
from src.util.byte_stream import ByteStream
from src.mini_tcp.reassembler import Reassembler
import random

class TCPReceiverTestHarness:
    def __init__(self, test_name, capacity):
        self.test_name = test_name
        self.output = ByteStream(capacity)
        self.reassembler = Reassembler(self.output)
        self.receiver = TCPReceiver(self.reassembler)

    def execute(self, action):
        action(self.receiver)

    def read_all(self) -> bytes:
        """Read all available data from the output stream"""
        data = self.output.peek(self.output.bytes_buffered())
        self.output.pop(len(data))
        return data
        
    def expect_ackno(self, ackno: Wrap32 | None) -> None:
        """Verify the acknowledgment number"""
        actual_ackno = self.receiver.send().ackno
        if ackno is None:
            assert actual_ackno is None, f"{self.test_name}: Expected no ackno but got {actual_ackno}"
        else:
            assert actual_ackno == ackno, f"{self.test_name}: Expected ackno {ackno} but got {actual_ackno}"
            
    def expect_window_size(self, window_size: int) -> None:
        """Verify the window size"""
        actual_window_size = self.receiver.send().window_size
        assert actual_window_size == window_size, f"{self.test_name}: Expected window size {window_size} but got {actual_window_size}"
        
    def expect_data(self, data: bytes) -> None:
        """Verify the received data"""
        actual_data = self.read_all()
        assert actual_data == data, f"{self.test_name}: Expected data {data} but got {actual_data}"
        
    def expect_bytes_pending(self, n: int) -> None:
        """Verify the number of bytes pending in reassembler"""
        actual_pending = self.reassembler.count_bytes_pending()
        assert actual_pending == n, f"{self.test_name}: Expected {n} bytes pending but got {actual_pending}"
        
    def expect_bytes_pushed(self, n: int) -> None:
        """Verify the number of bytes pushed to output"""
        actual_pushed = self.output.bytes_pushed()
        assert actual_pushed == n, f"{self.test_name}: Expected {n} bytes pushed but got {actual_pushed}"
        
    def expect_state(self, *, ackno: Wrap32 | None = None, window_size: int | None = None, 
                    data: bytes | None = None, bytes_pending: int | None = None, 
                    bytes_pushed: int | None = None) -> None:
        """Verify multiple state conditions at once"""
        if ackno is not None:
            self.expect_ackno(ackno)
        if window_size is not None:
            self.expect_window_size(window_size)
        if data is not None:
            self.expect_data(data)
        if bytes_pending is not None:
            self.expect_bytes_pending(bytes_pending)
        if bytes_pushed is not None:
            self.expect_bytes_pushed(bytes_pushed)
            
    def expect_closed(self) -> None:
        """Verify that the output stream is closed"""
        assert self.output.is_closed(), f"{self.test_name}: Expected output stream to be closed but it wasn't"

class TestTCPReceiver(unittest.TestCase):
    def test_connect_1(self):
        test = TCPReceiverTestHarness("connect 1", 4000)
        test.expect_state(window_size=4000, ackno=None, bytes_pending=0, bytes_pushed=0)
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(0), payload=b"", SYN=True)))
        test.expect_state(ackno=Wrap32(1), bytes_pending=0, bytes_pushed=0)

    def test_connect_2(self):
        test = TCPReceiverTestHarness("connect 2", 5435)
        test.expect_state(ackno=None, bytes_pending=0, bytes_pushed=0)
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(89347598), payload=b"", SYN=True)))
        test.expect_state(ackno=Wrap32(89347599), bytes_pending=0, bytes_pushed=0)

    def test_connect_3(self):
        test = TCPReceiverTestHarness("connect 3", 5435)
        test.expect_state(ackno=None, bytes_pending=0, bytes_pushed=0)
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(893475), payload=b"", SYN=False)))
        test.expect_state(ackno=None, bytes_pending=0, bytes_pushed=0)

    def test_connect_4(self):
        test = TCPReceiverTestHarness("connect 4", 5435)
        test.expect_state(ackno=None, bytes_pending=0, bytes_pushed=0)
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(893475), payload=b"", FIN=True)))
        test.expect_state(ackno=None, bytes_pending=0, bytes_pushed=0)

    def test_connect_5(self):
        test = TCPReceiverTestHarness("connect 5", 5435)
        test.expect_state(ackno=None, bytes_pending=0, bytes_pushed=0)
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(893475), payload=b"", FIN=True)))
        test.expect_state(ackno=None, bytes_pending=0, bytes_pushed=0)
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(89347598), payload=b"", SYN=True)))
        test.expect_state(ackno=Wrap32(89347599), bytes_pending=0, bytes_pushed=0)

    def test_connect_6(self):
        test = TCPReceiverTestHarness("connect 6", 4000)
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(5), payload=b"", SYN=True, FIN=True)))
        test.expect_closed()
        test.expect_state(ackno=Wrap32(7), bytes_pending=0, bytes_pushed=0)

    def test_window_size(self):
        # Test window size zero
        test = TCPReceiverTestHarness("window size zero", 0)
        test.expect_window_size(0)

        # Test window size 50
        test = TCPReceiverTestHarness("window size 50", 50)
        test.expect_window_size(50)

        # Test window size at max (65535)
        test = TCPReceiverTestHarness("window size at max", 65535)
        test.expect_window_size(65535)

        # Test window size at max+1
        test = TCPReceiverTestHarness("window size at max+1", 65536)
        test.expect_window_size(65535)

        # Test window size at max+5
        test = TCPReceiverTestHarness("window size at max+5", 65540)
        test.expect_window_size(65535)

        # Test window size at 10M
        test = TCPReceiverTestHarness("window size at 10M", 10000000)
        test.expect_window_size(65535)

    def test_in_window_later_segment(self):
        isn = random.randint(0, 0xFFFFFFFF)
        test = TCPReceiverTestHarness("in-window, later segment", 2358)
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn), payload=b"", SYN=True)))
        test.expect_ackno(Wrap32(isn + 1))
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn + 10), payload=b"abcd")))
        test.expect_state(ackno=Wrap32(isn + 1), data=b"", bytes_pending=4, bytes_pushed=0)

    def test_in_window_later_segment_then_hole_filled(self):
        isn = random.randint(0, 0xFFFFFFFF)
        test = TCPReceiverTestHarness("in-window, later segment, then hole filled", 2358)
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn), payload=b"", SYN=True)))
        test.expect_ackno(Wrap32(isn + 1))
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn + 5), payload=b"efgh")))
        test.expect_state(ackno=Wrap32(isn + 1), data=b"", bytes_pending=4, bytes_pushed=0)
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn + 1), payload=b"abcd")))
        test.expect_state(ackno=Wrap32(isn + 9), data=b"abcdefgh", bytes_pending=0, bytes_pushed=8)

    def test_hole_filled_bit_by_bit(self):
        isn = random.randint(0, 0xFFFFFFFF)
        test = TCPReceiverTestHarness("hole filled bit-by-bit", 2358)
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn), payload=b"", SYN=True)))
        test.expect_ackno(Wrap32(isn + 1))
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn + 5), payload=b"efgh")))
        test.expect_state(ackno=Wrap32(isn + 1), data=b"", bytes_pending=4, bytes_pushed=0)
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn + 1), payload=b"ab")))
        test.expect_state(ackno=Wrap32(isn + 3), data=b"ab", bytes_pending=4, bytes_pushed=2)
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn + 3), payload=b"cd")))
        test.expect_state(ackno=Wrap32(isn + 9), data=b"cdefgh", bytes_pending=0, bytes_pushed=8)

    def test_many_gaps_filled_bit_by_bit(self):
        isn = random.randint(0, 0xFFFFFFFF)
        test = TCPReceiverTestHarness("many gaps, filled bit-by-bit", 2358)
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn), payload=b"", SYN=True)))
        test.expect_ackno(Wrap32(isn + 1))
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn + 5), payload=b"e")))
        test.expect_state(ackno=Wrap32(isn + 1), data=b"", bytes_pending=1, bytes_pushed=0)
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn + 7), payload=b"g")))
        test.expect_state(ackno=Wrap32(isn + 1), data=b"", bytes_pending=2, bytes_pushed=0)
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn + 3), payload=b"c")))
        test.expect_state(ackno=Wrap32(isn + 1), data=b"", bytes_pending=3, bytes_pushed=0)
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn + 1), payload=b"ab")))
        test.expect_state(ackno=Wrap32(isn + 4), data=b"abc", bytes_pending=2, bytes_pushed=3)
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn + 6), payload=b"f")))
        test.expect_state(ackno=Wrap32(isn + 4), data=b"", bytes_pending=3, bytes_pushed=3)
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn + 4), payload=b"d")))
        test.expect_state(ackno=Wrap32(isn + 8), data=b"defg", bytes_pending=0, bytes_pushed=7)

    def test_many_gaps_then_subsumed(self):
        isn = random.randint(0, 0xFFFFFFFF)
        test = TCPReceiverTestHarness("many gaps, then subsumed", 2358)
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn), payload=b"", SYN=True)))
        test.expect_ackno(Wrap32(isn + 1))
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn + 5), payload=b"e")))
        test.expect_state(ackno=Wrap32(isn + 1), data=b"", bytes_pending=1, bytes_pushed=0)
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn + 7), payload=b"g")))
        test.expect_state(ackno=Wrap32(isn + 1), data=b"", bytes_pending=2, bytes_pushed=0)
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn + 3), payload=b"c")))
        test.expect_state(ackno=Wrap32(isn + 1), data=b"", bytes_pending=3, bytes_pushed=0)
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn + 1), payload=b"abcdefgh")))
        test.expect_state(ackno=Wrap32(isn + 9), data=b"abcdefgh", bytes_pending=0, bytes_pushed=8)

    def test_transmit_1(self):
        test = TCPReceiverTestHarness("transmit 1", 4000)
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(0), payload=b"", SYN=True)))
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(1), payload=b"abcd")))
        test.expect_state(ackno=Wrap32(5), data=b"abcd", bytes_pending=0, bytes_pushed=4)

    def test_transmit_2(self):
        isn = 384678
        test = TCPReceiverTestHarness("transmit 2", 4000)
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn), payload=b"", SYN=True)))
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn + 1), payload=b"abcd")))
        test.expect_state(ackno=Wrap32(isn + 5), bytes_pending=0, bytes_pushed=4)
        test.expect_data(b"abcd")
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn + 5), payload=b"efgh")))
        test.expect_state(ackno=Wrap32(isn + 9), bytes_pending=0, bytes_pushed=8)
        test.expect_data(b"efgh")

    def test_transmit_3(self):
        isn = 5
        test = TCPReceiverTestHarness("transmit 3", 4000)
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn), payload=b"", SYN=True)))
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn + 1), payload=b"abcd")))
        test.expect_state(ackno=Wrap32(isn + 5), bytes_pending=0, bytes_pushed=4)
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn + 5), payload=b"efgh")))
        test.expect_state(ackno=Wrap32(isn + 9), bytes_pending=0, bytes_pushed=8)
        test.expect_data(b"abcdefgh")

    def test_transmit_4(self):
        """Many (arrive/read)s"""
        test = TCPReceiverTestHarness("transmit 4", 4000)
        max_block_size = 10
        n_rounds = 10000
        isn = 893472
        bytes_sent = 0
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn), payload=b"", SYN=True)))
        
        for i in range(n_rounds):
            block_size = random.randint(1, max_block_size)
            data = ''.join(chr(ord('a') + ((i + j) % 26)) for j in range(block_size))
            
            test.expect_state(ackno=Wrap32(isn + bytes_sent + 1), bytes_pushed=bytes_sent)
            test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn + bytes_sent + 1), payload=data.encode())))
            bytes_sent += block_size
            test.expect_data(data.encode())

    def test_transmit_5(self):
        """Many arrives, one read"""
        max_block_size = 10
        n_rounds = 100
        test = TCPReceiverTestHarness("transmit 5", max_block_size * n_rounds)
        isn = 238
        bytes_sent = 0
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn), payload=b"", SYN=True)))
        
        all_data = ""
        for i in range(n_rounds):
            block_size = random.randint(1, max_block_size)
            data = ''.join(chr(ord('a') + ((i + j) % 26)) for j in range(block_size))
            all_data += data
            
            test.expect_state(ackno=Wrap32(isn + bytes_sent + 1), bytes_pushed=bytes_sent)
            test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn + bytes_sent + 1), payload=data.encode())))
            bytes_sent += block_size
            
        test.expect_data(all_data.encode())

if __name__ == '__main__':
    unittest.main() 