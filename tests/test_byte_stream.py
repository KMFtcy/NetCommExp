import unittest
from src.sponge.byte_stream import ByteStream

class TestByteStream(unittest.TestCase):
    def setUp(self):
        self.stream = ByteStream(capacity=10)

    def test_push_within_capacity(self):
        data = b"12345"
        pushed_bytes = self.stream.push(data)
        self.assertEqual(pushed_bytes, len(data))
        self.assertEqual(self.stream.bytes_buffered(), len(data))

    def test_push_exceeding_capacity(self):
        data = b"12345678901"
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

if __name__ == "__main__":
    unittest.main() 