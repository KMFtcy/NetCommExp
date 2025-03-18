import unittest
from src.sponge.byte_stream import ByteStream
from src.sponge.reassembler import Reassembler

class TestReassembler(unittest.TestCase):
    def setUp(self):
        self.stream = ByteStream(capacity=100)
        self.reassembler = Reassembler(self.stream)

    def test_insert_in_order(self):
        data = b"hello"
        self.reassembler.insert(0, data, False)
        self.assertEqual(self.stream.bytes_buffered(), len(data))
        self.assertEqual(self.stream.pop(len(data)), data)

    def test_insert_out_of_order(self):
        data1 = b"world"
        data2 = b"hello"
        self.reassembler.insert(5, data1, False)  # Out of order
        self.assertEqual(self.stream.bytes_buffered(), 0)  # Should not be added
        self.reassembler.insert(0, data2, False)  # In order
        self.assertEqual(self.stream.bytes_buffered(), len(data2))
        self.assertEqual(self.stream.pop(len(data2)), data2)
        self.reassembler.insert(5, data1, False)  # Now in order
        self.assertEqual(self.stream.bytes_buffered(), len(data1))
        self.assertEqual(self.stream.pop(len(data1)), data1)

    def test_insert_with_eof(self):
        data = b"hello"
        self.reassembler.insert(0, data, True)
        self.assertTrue(self.stream.is_closed())
        self.assertEqual(self.stream.bytes_buffered(), len(data))
        self.assertEqual(self.stream.pop(len(data)), data)

if __name__ == "__main__":
    unittest.main() 