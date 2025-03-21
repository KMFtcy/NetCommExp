import unittest
from src.sponge.byte_stream import ByteStream
import time

class TestByteStream(unittest.TestCase):
    def setUp(self):
        self.stream = ByteStream(capacity=1000)

    def test_push_within_capacity(self):
        data = b"12345"
        pushed_bytes = self.stream.push(data)
        self.assertEqual(pushed_bytes, len(data))
        self.assertEqual(self.stream.bytes_buffered(), len(data))

    def test_push_exceeding_capacity(self):
        data = b"12345678901"*1000
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

class TestByteStreamPerformance(unittest.TestCase):
    def measure_throughput(self, stream: ByteStream, packet_size: int, num_operations: int) -> tuple[float, float]:
        # Prepare test data
        test_data = bytes([i % 256 for i in range(packet_size)])
        total_bytes = packet_size * num_operations

        # Measure push performance
        start_time = time.time()
        for _ in range(num_operations):
            stream.push(test_data)
        push_duration = time.time() - start_time
        push_throughput = total_bytes / push_duration  # bytes per second

        # Measure pop performance
        start_time = time.time()
        for _ in range(num_operations):
            stream.pop(packet_size)
        pop_duration = time.time() - start_time
        pop_throughput = total_bytes / pop_duration  # bytes per second

        return push_throughput, pop_throughput

    def test_throughput_performance(self):
        # Test parameters
        packet_sizes = [4096, 1024, 512, 256, 128, 64, 32]  # bytes
        buffer_size = 1024 * 1024  # 1MB buffer
        operations = 100  # number of push/pop operations for each test

        print("\nByte Stream Throughput Test")
        print("=" * 50)
        print(f"Buffer Size: {buffer_size} bytes")
        print(f"Operations per test: {operations}")
        print("-" * 50)
        print("Packet Size | Push Throughput | Pop Throughput")
        print("-" * 50)

        for packet_size in packet_sizes:
            # Create a new stream for each test
            stream = ByteStream(buffer_size)
            
            # Measure throughput
            push_throughput, pop_throughput = self.measure_throughput(
                stream, packet_size, operations
            )

            # Convert to MB/s for display
            push_throughput_mb = push_throughput / (1024 * 1024)
            pop_throughput_mb = pop_throughput / (1024 * 1024)

            print(f"{packet_size:^11d} | {push_throughput_mb:^14.2f} | {pop_throughput_mb:^13.2f} MB/s")

            # Assert minimum performance requirements
            # min_throughput = 10 * 1024 * 1024  # 10 MB/s in bytes/s
            # self.assertGreater(
            #     push_throughput, 
            #     min_throughput, 
            #     f"Push throughput too low for {packet_size} byte packets"
            # )
            # self.assertGreater(
            #     pop_throughput, 
            #     min_throughput, 
            #     f"Pop throughput too low for {packet_size} byte packets"
            # )

        print("-" * 50)

if __name__ == "__main__":
    unittest.main(verbosity=2) 