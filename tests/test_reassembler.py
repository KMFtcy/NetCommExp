import unittest
from src.sponge.byte_stream import ByteStream
from src.sponge.reassembler import Reassembler
import time
class TestReassembler(unittest.TestCase):
    def setUp(self):
        self.reassembler = Reassembler(capacity=1000000)

    def test_insert_in_order(self):
        data = b"hello"
        self.reassembler.insert(0, data, False)
        self.assertEqual(self.reassembler.output.bytes_buffered(), len(data))
        self.assertEqual(self.reassembler.output.pop(len(data)), data)

    def test_insert_out_of_order(self):
        data1 = b"world"
        data2 = b"hello"
        self.reassembler.insert(5, data1, False)  # Out of order
        self.assertEqual(self.reassembler.output.bytes_buffered(), 0)  # Should not be added
        self.reassembler.insert(0, data2, False)  # In order
        self.assertEqual(self.reassembler.output.bytes_buffered(), len(data2))
        self.assertEqual(self.reassembler.output.pop(len(data2)), data2)
        self.reassembler.insert(5, data1, False)  # Now in order
        self.assertEqual(self.reassembler.output.bytes_buffered(), len(data1))
        self.assertEqual(self.reassembler.output.pop(len(data1)), data1)

    def test_insert_with_eof(self):
        data = b"hello"
        self.reassembler.insert(0, data, True)
        self.assertTrue(self.reassembler.output.is_closed())
        self.assertEqual(self.reassembler.output.bytes_buffered(), len(data))
        self.assertEqual(self.reassembler.output.pop(len(data)), data)

    def test_insert_performance(self):
        data = b"hello" * 100
        start_time = time.time()
        self.reassembler.insert(0, data, False)
        end_time = time.time()
        print(f"Insert bandwidth: {len(data) * 8 / (end_time - start_time) / 1e6} MBits/second")

if __name__ == "__main__":
    unittest.main() 