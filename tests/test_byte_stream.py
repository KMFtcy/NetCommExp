import unittest
from src.sponge.byte_stream import ByteStream
import time
class TestByteStream(unittest.TestCase):
    def setUp(self):
        self.stream = ByteStream(capacity=1000000)

    def test_push_within_capacity(self):
        data = b"12345"
        pushed_bytes = self.stream.push(data)
        self.assertEqual(pushed_bytes, len(data))
        self.assertEqual(self.stream.bytes_buffered(), len(data))

    def test_push_exceeding_capacity(self):
        data = b"12345678901"*1000000
        with self.assertRaises(ValueError):
            self.stream.push(data)

    def test_close_stream(self):
        self.stream.close()
        self.assertTrue(self.stream.is_closed())

    def test_push_to_closed_stream(self):
        self.stream.close()
        with self.assertRaises(ValueError):
            self.stream.push(b"123")

    def test_peek(self):
        data = b"12345"
        self.stream.push(data)
        self.assertEqual(bytes(self.stream.peek(3)), b"123")

    def test_pop(self):
        data = b"12345"
        self.stream.push(data)
        popped_data = self.stream.pop(3)
        self.assertEqual(bytes(popped_data), b"123")
        self.assertEqual(self.stream.bytes_popped(), 3)

    def test_is_finished(self):
        data = b"12345"
        self.stream.push(data)
        self.stream.pop(5)
        self.stream.close()
        self.assertTrue(self.stream.is_finished())

    def test_push_performance(self):
        data = b"12345" * 1000
        start_time = time.time()
        self.stream.push(data)
        end_time = time.time()
        # print bandwidth in MBits/second
        print(f"Push bandwidth: {len(data) * 8 / (end_time - start_time) / 1e6} MBits/second")

    def test_pop_performance(self):
        data = b"12345" * 1000
        self.stream.push(data)
        start_time = time.time()
        self.stream.pop(len(data))
        end_time = time.time()
        # print bandwidth in MBits/second
        print(f"Pop bandwidth: {len(data) * 8 / (end_time - start_time) / 1e6} MBits/second")

if __name__ == "__main__":
    unittest.main() 