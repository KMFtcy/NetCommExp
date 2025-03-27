import time
import unittest
from src.util.ringbuffer import RingBuffer

class TestRingBuffer(unittest.TestCase):
    def test_buffer_state(self):
        # Create a buffer with capacity of 128 bytes
        buffer = RingBuffer(128)
        
        # Test initial state
        self.assertEqual(len(buffer), 0)
        self.assertEqual(buffer.get_available_space(), 128)
        self.assertTrue(buffer.is_empty())
        self.assertFalse(buffer.is_full())
        
        # Test after pushing some data
        data1 = b"Hello"  # 5 bytes
        buffer.push(data1)
        self.assertEqual(len(buffer), 5)
        self.assertEqual(buffer.get_available_space(), 123)
        self.assertFalse(buffer.is_empty())
        self.assertFalse(buffer.is_full())
        
        # Test after filling the buffer
        data2 = bytes([i % 256 for i in range(123)])  # Fill the remaining space
        buffer.push(data2)
        self.assertEqual(len(buffer), 128)
        self.assertEqual(buffer.get_available_space(), 0)
        self.assertFalse(buffer.is_empty())
        self.assertTrue(buffer.is_full())
        
        # Test after popping some data
        buffer.pop(20)
        self.assertEqual(len(buffer), 108)
        self.assertEqual(buffer.get_available_space(), 20)
        self.assertFalse(buffer.is_empty())
        self.assertFalse(buffer.is_full())
        
        # Test wrap-around scenario
        buffer.push(bytes([0] * 15))  # Push 15 bytes
        self.assertEqual(len(buffer), 123)
        self.assertEqual(buffer.get_available_space(), 5)
        
        # Test after emptying the buffer
        buffer.pop(123)
        self.assertEqual(len(buffer), 0)
        self.assertEqual(buffer.get_available_space(), 128)
        self.assertTrue(buffer.is_empty())
        self.assertFalse(buffer.is_full())

    def test_data_correctness_with_wraparound(self):
        # Create a small buffer to easily test wrap-around
        buffer_size = 128
        buffer = RingBuffer(buffer_size)
        
        # Test data
        data1 = b"Hello"  # 5 bytes
        data2 = b"World"  # 5 bytes
        data3 = bytes([i % 256 for i in range(110)])  # 110 bytes
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
        read_data = buffer.pop(110)  # Read data3
        self.assertEqual(read_data, data3)
        
        read_data = buffer.pop(14)  # Read data4
        self.assertEqual(read_data, data4)
        
        # Step 3: Test multiple wrap-arounds
        # Fill the buffer almost completely
        large_data = bytes([i % 256 for i in range(120)])
        buffer.push(large_data)
        
        # Read half and write more to force wrap-around
        half_size = 60
        first_half = buffer.pop(half_size)
        self.assertEqual(first_half, large_data[:half_size])
        
        # Push data that will wrap around
        wrap_data = bytes([i % 256 for i in range(65)])
        buffer.push(wrap_data)
        
        # Verify remaining data
        remaining_first = buffer.pop(60)  # Remaining from large_data
        self.assertEqual(remaining_first, large_data[half_size:120])
        
        wrap_result = buffer.pop(65)  # Should read the wrapped around data
        self.assertEqual(wrap_result, wrap_data)
        
        # Step 4: Test edge case - fill exactly to buffer end
        exact_size = buffer_size - len(buffer)
        edge_data = bytes([i % 256 for i in range(exact_size)])
        buffer.push(edge_data)
        
        # Verify the edge data
        self.assertEqual(buffer.pop(exact_size), edge_data)
        
        # Step 5: Test error conditions
        with self.assertRaises(OverflowError):
            buffer.push(bytes([0] * (buffer_size + 1)))
            
        # with self.assertRaises(ValueError):
        #     buffer.pop(buffer_size + 1)
            
        # Step 6: Test peek with wrap-around
        buffer.push(bytes([0] * 30))
        buffer.pop(30)  # Move head forward
        test_data = bytes([i % 256 for i in range(100)])
        buffer.push(test_data)
        
        # Peek should handle wrap-around correctly
        peek_result = buffer.peek(100)  # This should peek across the wrap-around boundary
        self.assertEqual(peek_result, test_data)

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

class TestRingBufferConcurrency(unittest.TestCase):
    def test_concurrent_read_write(self):
        import threading
        import queue
        import random
        import time

        # Test parameters
        BUFFER_SIZE = 1024 * 1024  # 1MB buffer
        TEST_DURATION = 3  # seconds
        PACKET_SIZE_MIN = 1024  # 1KB
        PACKET_SIZE_MAX = 4096  # 4KB

        # get a random time value between 0.001 and 0.01
        def get_random_time():
            return random.uniform(0.001, 0.01)
        
        # Create buffer and test data
        buffer = RingBuffer(BUFFER_SIZE)
        error_queue = queue.Queue()
        stop_event = threading.Event()
        
        # Statistics
        stats = {
            'bytes_written': 0,
            'bytes_read': 0,
            'write_ops': 0,
            'read_ops': 0
        }

        def writer_thread():
            try:
                while not stop_event.is_set():
                    # Generate random sized packet
                    packet_size = random.randint(PACKET_SIZE_MIN, PACKET_SIZE_MAX)
                    data = bytes([random.randint(0, 255) for _ in range(packet_size)])
                    
                    # Try to write if there's enough space
                    if buffer.get_available_space() >= packet_size:
                        buffer.push(data)
                        stats['bytes_written'] += packet_size
                        stats['write_ops'] += 1
                    else:
                        # Small sleep if buffer is full
                        time.sleep(get_random_time())
            except Exception as e:
                error_queue.put(f"Writer error: {str(e)}")

        def reader_thread():
            try:
                while not stop_event.is_set():
                    # Try to read if there's data available
                    if buffer.get_available_space() > 0:
                        # Read a random amount of available data
                        available = buffer.get_available_space()
                        read_size = random.randint(1, min(available, PACKET_SIZE_MAX))
                        data = buffer.pop(read_size)
                        stats['bytes_read'] += len(data)
                        stats['read_ops'] += 1
                    else:
                        # Small sleep if buffer is empty
                        time.sleep(get_random_time())
            except Exception as e:
                error_queue.put(f"Reader error: {str(e)}")

        # Create and start threads
        writer = threading.Thread(target=writer_thread)
        reader = threading.Thread(target=reader_thread)
        
        print("\nStarting concurrent read/write stress test...")
        start_time = time.time()
        
        writer.start()
        reader.start()
        
        # Run test for specified duration
        time.sleep(TEST_DURATION)
        stop_event.set()
        
        # Wait for threads to finish
        writer.join()
        reader.join()
        
        duration = time.time() - start_time
        
        # Check for any errors
        if not error_queue.empty():
            errors = []
            while not error_queue.empty():
                errors.append(error_queue.get())
            self.fail(f"Test failed with errors: {'; '.join(errors)}")
        
        # Print statistics
        print("\nConcurrent Read/Write Test Results")
        print("=" * 50)
        print(f"Test duration: {duration:.2f} seconds")
        print(f"Buffer size: {BUFFER_SIZE/1024:.0f}KB")
        print("-" * 50)
        print(f"Total bytes written: {stats['bytes_written']/1024/1024:.2f}MB")
        print(f"Total bytes read: {stats['bytes_read']/1024/1024:.2f}MB")
        print(f"Bytes remains in buffer: {len(buffer)/1024/1024:.2f}MB")
        print(f"Write operations: {stats['write_ops']}")
        print(f"Read operations: {stats['read_ops']}")
        print(f"Write throughput: {stats['bytes_written']/duration/1024/1024:.2f}MB/s")
        print(f"Read throughput: {stats['bytes_read']/duration/1024/1024:.2f}MB/s")
        print("-" * 50)
        
        # Verify test results
        self.assertEqual(stats['bytes_written'], stats['bytes_read'] + len(buffer), 
                        "Number of bytes written should equal number of bytes read plus the bytes in the buffer")
        self.assertGreater(stats['write_ops'], 0, "Should have performed some write operations")
        self.assertGreater(stats['read_ops'], 0, "Should have performed some read operations")

if __name__ == "__main__":
    unittest.main(verbosity=2)