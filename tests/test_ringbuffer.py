import time
import unittest
from src.util.ringbuffer import RingBuffer

class TestRingBuffer(unittest.TestCase):
    def test_buffer_state(self):
        # Create a buffer with capacity of 100 bytes
        buffer = RingBuffer(100)
        
        # Test initial state
        self.assertEqual(buffer.get_size(), 0)
        self.assertEqual(buffer.get_available_space(), 100)
        self.assertTrue(buffer.is_empty())
        self.assertFalse(buffer.is_full())
        
        # Test after pushing some data
        data1 = b"Hello"  # 5 bytes
        buffer.push(data1)
        self.assertEqual(buffer.get_size(), 5)
        self.assertEqual(buffer.get_available_space(), 95)
        self.assertFalse(buffer.is_empty())
        self.assertFalse(buffer.is_full())
        
        # Test after filling the buffer
        data2 = bytes([i % 256 for i in range(95)])  # Fill the remaining space
        buffer.push(data2)
        self.assertEqual(buffer.get_size(), 100)
        self.assertEqual(buffer.get_available_space(), 0)
        self.assertFalse(buffer.is_empty())
        self.assertTrue(buffer.is_full())
        
        # Test after popping some data
        buffer.pop(20)
        self.assertEqual(buffer.get_size(), 80)
        self.assertEqual(buffer.get_available_space(), 20)
        self.assertFalse(buffer.is_empty())
        self.assertFalse(buffer.is_full())
        
        # Test wrap-around scenario
        buffer.push(bytes([0] * 15))  # Push 15 bytes
        self.assertEqual(buffer.get_size(), 95)
        self.assertEqual(buffer.get_available_space(), 5)
        
        # Test after emptying the buffer
        buffer.pop(95)
        self.assertEqual(buffer.get_size(), 0)
        self.assertEqual(buffer.get_available_space(), 100)
        self.assertTrue(buffer.is_empty())
        self.assertFalse(buffer.is_full())

    def test_data_correctness_with_wraparound(self):
        # Create a small buffer to easily test wrap-around
        buffer_size = 100
        buffer = RingBuffer(buffer_size)
        
        # Test data
        data1 = b"Hello"  # 5 bytes
        data2 = b"World"  # 5 bytes
        data3 = bytes([i % 256 for i in range(80)])  # 80 bytes
        data4 = b"Longer Testing"  # 14 bytes
        
        # Step 1: Fill most of the buffer
        buffer.push(data1)
        buffer.push(data2)
        buffer.push(data3)
        
        # Verify initial data
        self.assertEqual(buffer.pop(5), data1)
        self.assertEqual(buffer.pop(5), data2)
        
        # Step 2: Now head is at position 10, tail at 90
        # Push data that will wrap around
        buffer.push(data4)  # This should wrap around
        
        # Read the remaining data
        read_data = buffer.pop(80)  # Read data3
        self.assertEqual(read_data, data3)
        
        read_data = buffer.pop(14)  # Read data4
        self.assertEqual(read_data, data4)
        
        # Step 3: Test multiple wrap-arounds
        # Fill the buffer almost completely
        large_data = bytes([i % 256 for i in range(95)])
        buffer.push(large_data)
        
        # Read half and write more to force wrap-around
        half_size = 50
        first_half = buffer.pop(half_size)
        self.assertEqual(first_half, large_data[:half_size])
        
        # Push data that will wrap around
        wrap_data = bytes([i % 256 for i in range(50)])
        buffer.push(wrap_data)
        
        # Verify remaining data
        remaining_first = buffer.pop(45)  # Remaining from large_data
        self.assertEqual(remaining_first, large_data[half_size:95])
        
        wrap_result = buffer.pop(50)  # Should read the wrapped around data
        self.assertEqual(wrap_result, wrap_data)
        
        # Step 4: Test edge case - fill exactly to buffer end
        exact_size = buffer_size - buffer.size
        edge_data = bytes([i % 256 for i in range(exact_size)])
        buffer.push(edge_data)
        
        # Verify the edge data
        self.assertEqual(buffer.pop(exact_size), edge_data)
        
        # Step 5: Test error conditions
        with self.assertRaises(OverflowError):
            buffer.push(bytes([0] * (buffer_size + 1)))
            
        with self.assertRaises(ValueError):
            buffer.pop(buffer_size + 1)
            
        # Step 6: Test peek with wrap-around
        test_data = bytes([i % 256 for i in range(30)])
        buffer.push(test_data)
        buffer.pop(10)  # Move head forward
        buffer.push(bytes([0] * 70))  # Force wrap-around
        
        # Peek should handle wrap-around correctly
        peek_result = buffer.peek(20)  # This should peek across the wrap-around boundary
        self.assertEqual(peek_result, test_data[10:30])

class TestRingBufferPerformance(unittest.TestCase):
    def measure_throughput(self, buffer: RingBuffer, packet_size: int, num_operations: int) -> tuple[float, float]:
        # Prepare test data
        test_data = bytes([i % 256 for i in range(packet_size)])
        total_bytes = packet_size * num_operations

        # Measure push performance
        start_time = time.time()
        for _ in range(num_operations):
            buffer.push(test_data)
        push_duration = time.time() - start_time
        push_throughput = total_bytes / push_duration  # bytes per second

        # Measure pop performance
        start_time = time.time()
        for _ in range(num_operations):
            buffer.pop(packet_size)
        pop_duration = time.time() - start_time
        pop_throughput = total_bytes / pop_duration  # bytes per second

        return push_throughput, pop_throughput

    def test_throughput_performance(self):
        # Test parameters
        packet_sizes = [4096, 1024, 512, 256, 128, 64, 32]  # bytes
        buffer_size = 1024 * 1024  # 1MB buffer
        operations = 100  # number of push/pop operations for each test

        print("\nRing Buffer Throughput Test")
        print("=" * 50)
        print(f"Buffer Size: {buffer_size} bytes")
        print(f"Operations per test: {operations}")
        print("-" * 50)
        print("Packet Size | Push Throughput | Pop Throughput")
        print("-" * 50)

        for packet_size in packet_sizes:
            # Create a new buffer for each test
            buffer = RingBuffer(buffer_size)
            
            # Measure throughput
            push_throughput, pop_throughput = self.measure_throughput(
                buffer, packet_size, operations
            )

            # Convert to MB/s for display
            push_throughput_mb = push_throughput / (1024 * 1024)
            pop_throughput_mb = pop_throughput / (1024 * 1024)

            print(f"{packet_size:^11d} | {push_throughput_mb:^14.2f} | {pop_throughput_mb:^13.2f} MB/s")

            # Assert minimum performance requirements
            min_throughput = 10 * 1024 * 1024  # 10 MB/s in bytes/s
            self.assertGreater(
                push_throughput, 
                min_throughput, 
                f"Push throughput too low for {packet_size} byte packets"
            )
            self.assertGreater(
                pop_throughput, 
                min_throughput, 
                f"Pop throughput too low for {packet_size} byte packets"
            )

        print("-" * 50)

if __name__ == "__main__":
    unittest.main(verbosity=2)