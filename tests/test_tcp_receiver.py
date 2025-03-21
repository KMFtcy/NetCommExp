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

class TestTCPReceiver(unittest.TestCase):
    def test_connect_1(self):
        test = TCPReceiverTestHarness("connect 1", 4000)
        self.assertEqual(test.receiver.send().window_size, 4000)
        self.assertIsNone(test.receiver.send().ackno)
        self.assertEqual(test.reassembler.count_bytes_pending(), 0)
        self.assertEqual(test.output.bytes_pushed(), 0)
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(0), payload=b"", SYN=True)))
        self.assertEqual(test.receiver.send().ackno, Wrap32(1))
        self.assertEqual(test.reassembler.count_bytes_pending(), 0)
        self.assertEqual(test.output.bytes_pushed(), 0)

    def test_connect_2(self):
        test = TCPReceiverTestHarness("connect 2", 5435)
        self.assertIsNone(test.receiver.send().ackno)
        self.assertEqual(test.reassembler.count_bytes_pending(), 0)
        self.assertEqual(test.output.bytes_pushed(), 0)
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(89347598), payload=b"", SYN=True)))
        self.assertEqual(test.receiver.send().ackno, Wrap32(89347599))
        self.assertEqual(test.reassembler.count_bytes_pending(), 0)
        self.assertEqual(test.output.bytes_pushed(), 0)

    def test_connect_3(self):
        test = TCPReceiverTestHarness("connect 3", 5435)
        self.assertIsNone(test.receiver.send().ackno)
        self.assertEqual(test.reassembler.count_bytes_pending(), 0)
        self.assertEqual(test.output.bytes_pushed(), 0)
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(893475), payload=b"", SYN=False)))
        self.assertIsNone(test.receiver.send().ackno)
        self.assertEqual(test.reassembler.count_bytes_pending(), 0)
        self.assertEqual(test.output.bytes_pushed(), 0)

    def test_connect_4(self):
        test = TCPReceiverTestHarness("connect 4", 5435)
        self.assertIsNone(test.receiver.send().ackno)
        self.assertEqual(test.reassembler.count_bytes_pending(), 0)
        self.assertEqual(test.output.bytes_pushed(), 0)
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(893475), payload=b"", FIN=True)))
        self.assertIsNone(test.receiver.send().ackno)
        self.assertEqual(test.reassembler.count_bytes_pending(), 0)
        self.assertEqual(test.output.bytes_pushed(), 0)

    def test_connect_5(self):
        test = TCPReceiverTestHarness("connect 5", 5435)
        self.assertIsNone(test.receiver.send().ackno)
        self.assertEqual(test.reassembler.count_bytes_pending(), 0)
        self.assertEqual(test.output.bytes_pushed(), 0)
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(893475), payload=b"", FIN=True)))
        self.assertIsNone(test.receiver.send().ackno)
        self.assertEqual(test.reassembler.count_bytes_pending(), 0)
        self.assertEqual(test.output.bytes_pushed(), 0)
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(89347598), payload=b"", SYN=True)))
        self.assertEqual(test.receiver.send().ackno, Wrap32(89347599))
        self.assertEqual(test.reassembler.count_bytes_pending(), 0)
        self.assertEqual(test.output.bytes_pushed(), 0)

    def test_connect_6(self):
        test = TCPReceiverTestHarness("connect 6", 4000)
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(5), payload=b"", SYN=True, FIN=True)))
        self.assertTrue(test.output.is_closed())
        self.assertEqual(test.receiver.send().ackno, Wrap32(7))
        self.assertEqual(test.reassembler.count_bytes_pending(), 0)
        self.assertEqual(test.output.bytes_pushed(), 0)

    def test_window_size(self):
        # Test window size zero
        test = TCPReceiverTestHarness("window size zero", 0)
        self.assertEqual(test.receiver.send().window_size, 0)

        # Test window size 50
        test = TCPReceiverTestHarness("window size 50", 50)
        self.assertEqual(test.receiver.send().window_size, 50)

        # Test window size at max (65535)
        test = TCPReceiverTestHarness("window size at max", 65535)
        self.assertEqual(test.receiver.send().window_size, 65535)

        # Test window size at max+1
        test = TCPReceiverTestHarness("window size at max+1", 65536)
        self.assertEqual(test.receiver.send().window_size, 65535)

        # Test window size at max+5
        test = TCPReceiverTestHarness("window size at max+5", 65540)
        self.assertEqual(test.receiver.send().window_size, 65535)

        # Test window size at 10M
        test = TCPReceiverTestHarness("window size at 10M", 10000000)
        self.assertEqual(test.receiver.send().window_size, 65535)

    def test_in_window_later_segment(self):
        # Generate random ISN
        isn = random.randint(0, 0xFFFFFFFF)
        test = TCPReceiverTestHarness("in-window, later segment", 2358)
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn), payload=b"", SYN=True)))
        self.assertEqual(test.receiver.send().ackno, Wrap32(isn + 1))
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn + 10), payload=b"abcd")))
        self.assertEqual(test.receiver.send().ackno, Wrap32(isn + 1))
        self.assertEqual(test.read_all(), b"")
        self.assertEqual(test.reassembler.count_bytes_pending(), 4)
        self.assertEqual(test.output.bytes_pushed(), 0)

    def test_in_window_later_segment_then_hole_filled(self):
        isn = random.randint(0, 0xFFFFFFFF)
        test = TCPReceiverTestHarness("in-window, later segment, then hole filled", 2358)
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn), payload=b"", SYN=True)))
        self.assertEqual(test.receiver.send().ackno, Wrap32(isn + 1))
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn + 5), payload=b"efgh")))
        self.assertEqual(test.receiver.send().ackno, Wrap32(isn + 1))
        self.assertEqual(test.read_all(), b"")
        self.assertEqual(test.reassembler.count_bytes_pending(), 4)
        self.assertEqual(test.output.bytes_pushed(), 0)
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn + 1), payload=b"abcd")))
        self.assertEqual(test.receiver.send().ackno, Wrap32(isn + 9))
        self.assertEqual(test.read_all(), b"abcdefgh")
        self.assertEqual(test.reassembler.count_bytes_pending(), 0)
        self.assertEqual(test.output.bytes_pushed(), 8)

    def test_hole_filled_bit_by_bit(self):
        isn = random.randint(0, 0xFFFFFFFF)
        test = TCPReceiverTestHarness("hole filled bit-by-bit", 2358)
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn), payload=b"", SYN=True)))
        self.assertEqual(test.receiver.send().ackno, Wrap32(isn + 1))
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn + 5), payload=b"efgh")))
        self.assertEqual(test.receiver.send().ackno, Wrap32(isn + 1))
        self.assertEqual(test.read_all(), b"")
        self.assertEqual(test.reassembler.count_bytes_pending(), 4)
        self.assertEqual(test.output.bytes_pushed(), 0)
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn + 1), payload=b"ab")))
        self.assertEqual(test.receiver.send().ackno, Wrap32(isn + 3))
        self.assertEqual(test.read_all(), b"ab")
        self.assertEqual(test.reassembler.count_bytes_pending(), 4)
        self.assertEqual(test.output.bytes_pushed(), 2)
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn + 3), payload=b"cd")))
        self.assertEqual(test.receiver.send().ackno, Wrap32(isn + 9))
        self.assertEqual(test.read_all(), b"cdefgh")
        self.assertEqual(test.reassembler.count_bytes_pending(), 0)
        self.assertEqual(test.output.bytes_pushed(), 8)

    def test_many_gaps_filled_bit_by_bit(self):
        isn = random.randint(0, 0xFFFFFFFF)
        test = TCPReceiverTestHarness("many gaps, filled bit-by-bit", 2358)
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn), payload=b"", SYN=True)))
        self.assertEqual(test.receiver.send().ackno, Wrap32(isn + 1))
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn + 5), payload=b"e")))
        self.assertEqual(test.receiver.send().ackno, Wrap32(isn + 1))
        self.assertEqual(test.read_all(), b"")
        self.assertEqual(test.reassembler.count_bytes_pending(), 1)
        self.assertEqual(test.output.bytes_pushed(), 0)
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn + 7), payload=b"g")))
        self.assertEqual(test.receiver.send().ackno, Wrap32(isn + 1))
        self.assertEqual(test.read_all(), b"")
        self.assertEqual(test.reassembler.count_bytes_pending(), 2)
        self.assertEqual(test.output.bytes_pushed(), 0)
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn + 3), payload=b"c")))
        self.assertEqual(test.receiver.send().ackno, Wrap32(isn + 1))
        self.assertEqual(test.read_all(), b"")
        self.assertEqual(test.reassembler.count_bytes_pending(), 3)
        self.assertEqual(test.output.bytes_pushed(), 0)
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn + 1), payload=b"ab")))
        self.assertEqual(test.receiver.send().ackno, Wrap32(isn + 4))
        self.assertEqual(test.read_all(), b"abc")
        self.assertEqual(test.reassembler.count_bytes_pending(), 2)
        self.assertEqual(test.output.bytes_pushed(), 3)
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn + 6), payload=b"f")))
        self.assertEqual(test.reassembler.count_bytes_pending(), 3)
        self.assertEqual(test.output.bytes_pushed(), 3)
        self.assertEqual(test.read_all(), b"")
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn + 4), payload=b"d")))
        self.assertEqual(test.reassembler.count_bytes_pending(), 0)
        self.assertEqual(test.output.bytes_pushed(), 7)
        self.assertEqual(test.read_all(), b"defg")

    def test_many_gaps_then_subsumed(self):
        isn = random.randint(0, 0xFFFFFFFF)
        test = TCPReceiverTestHarness("many gaps, then subsumed", 2358)
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn), payload=b"", SYN=True)))
        self.assertEqual(test.receiver.send().ackno, Wrap32(isn + 1))
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn + 5), payload=b"e")))
        self.assertEqual(test.receiver.send().ackno, Wrap32(isn + 1))
        self.assertEqual(test.read_all(), b"")
        self.assertEqual(test.reassembler.count_bytes_pending(), 1)
        self.assertEqual(test.output.bytes_pushed(), 0)
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn + 7), payload=b"g")))
        self.assertEqual(test.receiver.send().ackno, Wrap32(isn + 1))
        self.assertEqual(test.read_all(), b"")
        self.assertEqual(test.reassembler.count_bytes_pending(), 2)
        self.assertEqual(test.output.bytes_pushed(), 0)
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn + 3), payload=b"c")))
        self.assertEqual(test.receiver.send().ackno, Wrap32(isn + 1))
        self.assertEqual(test.read_all(), b"")
        self.assertEqual(test.reassembler.count_bytes_pending(), 3)
        self.assertEqual(test.output.bytes_pushed(), 0)
        
        test.execute(lambda r: r.receive(TCPSenderMessage(seqno=Wrap32(isn + 1), payload=b"abcdefgh")))
        self.assertEqual(test.receiver.send().ackno, Wrap32(isn + 9))
        self.assertEqual(test.read_all(), b"abcdefgh")
        self.assertEqual(test.reassembler.count_bytes_pending(), 0)
        self.assertEqual(test.output.bytes_pushed(), 8)

if __name__ == '__main__':
    unittest.main() 