import unittest
import threading
import queue
import time
import os
import sys
import random
import timeit
import statistics
from unittest.mock import MagicMock, patch

# Add project root directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.FEC.encoder import Encoder, CodeType
from src.util.byte_stream import ByteStream


class TestEncoder(unittest.TestCase):
    def setUp(self):
        # Create a mock ByteStream for testing
        self.mock_byte_stream = MagicMock(spec=ByteStream)
        self.mock_byte_stream.available_capacity.return_value = 1000
        
    def tearDown(self):
        # Ensure encoder is stopped after each test
        if hasattr(self, 'encoder') and self.encoder:
            self.encoder.stop()

    def test_init_reed_solomon(self):
        """Test initializing encoder with Reed-Solomon coding"""
        encoder = Encoder(self.mock_byte_stream, code_type=CodeType.REED_SOLOMON, n=100, k=70)
        self.assertEqual(encoder.code_type, CodeType.REED_SOLOMON)
        self.assertEqual(encoder.n, 100)
        self.assertEqual(encoder.k, 70)
        self.assertTrue(encoder.running)
        encoder.stop()
        

    def test_init_lt_coding(self):
        """Test initializing encoder with LT coding"""
        # Verify that LT coding initialization raises ValueError (unimplemented feature)
        with self.assertRaises(ValueError) as context:
            encoder = Encoder(self.mock_byte_stream, code_type=CodeType.LT_CODING, n=100, k=70)
        
        # Verify that the exception message is correct
        self.assertIn("LT Coding is not supported yet", str(context.exception))
        
        # No need to call encoder.stop() as the encoder object was not successfully created

    def test_encode_bytes_data(self):
        """Test encoding bytes type data"""
        k = 5
        encoder = Encoder(self.mock_byte_stream, n=10, k=k)
        # Ensure data length is a multiple of k (5)
        base_data = b"Hello, world! This is a test data for encoding."
        # Calculate padding needed
        remainder = len(base_data) % k
        padding = (k - remainder) if remainder > 0 else 0
        # Add padding to make data length a multiple of k
        test_data = base_data + b"\x00" * padding
        
        encoder.encode(test_data)
        
        # Give the encoding thread some time to process the data
        time.sleep(0.5)
        
        # Verify that ByteStream.push was called
        self.mock_byte_stream.push.assert_called()
        encoder.stop()

    def test_encode_list_data(self):
        """Test encoding list type data"""
        k = 5
        encoder = Encoder(self.mock_byte_stream, n=10, k=k)
        # Exactly k packets to match encoding parameter
        test_data = [b"packet1", b"packet2", b"packet3", b"packet4", b"packet5"]
        # Ensure all packets have the same length
        max_len = max(len(p) for p in test_data)
        padded_data = [p + b"\x00" * (max_len - len(p)) for p in test_data]
        
        encoder.encode(padded_data)
        
        # Give the encoding thread some time to process the data
        time.sleep(0.5)
        
        # Verify that ByteStream.push was called
        self.mock_byte_stream.push.assert_called()
        encoder.stop()
    
    def test_insufficient_space(self):
        """Test the case of insufficient ByteStream space"""
        # Simulate a ByteStream with very small capacity
        self.mock_byte_stream.available_capacity.return_value = 10
        encoder = Encoder(self.mock_byte_stream, n=10, k=5)
        
        # Create data larger than the allowed size
        test_data = b"This data is too large for the ByteStream"
        
        # Test if ValueError is raised
        with self.assertRaises(ValueError):
            encoder.encode(test_data)
            
        encoder.stop()

    def test_empty_data(self):
        """Test encoding empty data"""
        encoder = Encoder(self.mock_byte_stream, n=10, k=5)
        encoder.encode(b"")
        
        # Give the encoding thread some time to process the data
        time.sleep(0.5)
        
        # Verify that the encoding process doesn't crash
        encoder.stop()
        
    def test_small_data(self):
        """Test encoding small data (less than k)"""
        k = 5
        encoder = Encoder(self.mock_byte_stream, n=10, k=k)
        # Create data that's exactly a multiple of k
        test_data = b"small" + b"\x00" * (k - 5 % k)
        
        encoder.encode(test_data)
        
        # Give the encoding thread some time to process the data
        time.sleep(0.5)
        
        # Verify that ByteStream.push was called
        self.mock_byte_stream.push.assert_called()
        encoder.stop()
        
    def test_large_data(self):
        """Test encoding large data"""
        k = 5
        encoder = Encoder(self.mock_byte_stream, n=10, k=k)
        # Create data size that's a multiple of k
        data_size = 1000 + (k - 1000 % k) if 1000 % k != 0 else 1000
        large_data = bytes([random.randint(0, 255) for _ in range(data_size)])
        
        encoder.encode(large_data)
        
        # Give the encoding thread some time to process the data
        time.sleep(0.5)
        
        # Verify that ByteStream.push was called
        self.mock_byte_stream.push.assert_called()
        encoder.stop()
        
    def test_multiple_encode_calls(self):
        """Test multiple calls to the encode method"""
        k = 5
        encoder = Encoder(self.mock_byte_stream, n=10, k=k)
        
        # Call encode multiple times, ensure each call's data is a multiple of k
        for i in range(5):
            base_data = f"Test data {i}".encode()
            remainder = len(base_data) % k
            padding = (k - remainder) if remainder > 0 else 0
            padded_data = base_data + b"\x00" * padding
            
            encoder.encode(padded_data)
            time.sleep(0.1)  # Give some time to process
            
        # Verify that ByteStream.push was called 5 times
        self.assertEqual(self.mock_byte_stream.push.call_count, 5)
        encoder.stop()
        
    def test_stop_and_restart(self):
        """Test stopping and restarting the encoder"""
        encoder = Encoder(self.mock_byte_stream, n=10, k=5)
        self.assertTrue(encoder.running)
        
        # Stop the encoder
        encoder.stop()
        self.assertFalse(encoder.running)
        
        # Restart the encoder
        encoder.start()
        self.assertTrue(encoder.running)
        encoder.stop()
        
    def test_bytestream_full_during_encoding(self):
        """Test the case where ByteStream becomes full during encoding"""
        # First simulate that ByteStream has enough space
        k = 5
        self.mock_byte_stream.available_capacity.return_value = 1000
        encoder = Encoder(self.mock_byte_stream, n=10, k=k)
        
        # Simulate the case where ByteStream is full during push
        def side_effect(data):
            raise ValueError("ByteStream is full")
            
        self.mock_byte_stream.push.side_effect = side_effect
        
        # Try to encode data, ensure data is a multiple of k
        base_data = b"Test data"
        remainder = len(base_data) % k
        padding = (k - remainder) if remainder > 0 else 0
        test_data = base_data + b"\x00" * padding
        
        encoder.encode(test_data)
        
        # Give the encoding thread some time to process the data
        time.sleep(0.5)
        
        # Verify that push was called but encountered an error
        self.mock_byte_stream.push.assert_called()
        encoder.stop()
        
    def test_different_n_k_values(self):
        """Test different n and k values"""
        # Test the case where k is close to n
        k1 = 95
        encoder1 = Encoder(self.mock_byte_stream, n=100, k=k1)
        base_data1 = b"Test data for high k/n ratio"
        remainder1 = len(base_data1) % k1
        padding1 = (k1 - remainder1) if remainder1 > 0 else 0
        test_data1 = base_data1 + b"\x00" * padding1
        
        encoder1.encode(test_data1)
        time.sleep(0.5)
        encoder1.stop()
        
        # Test the case where k is much smaller than n
        k2 = 20
        encoder2 = Encoder(self.mock_byte_stream, n=100, k=k2)
        base_data2 = b"Test data for low k/n ratio"
        remainder2 = len(base_data2) % k2
        padding2 = (k2 - remainder2) if remainder2 > 0 else 0
        test_data2 = base_data2 + b"\x00" * padding2
        
        encoder2.encode(test_data2)
        time.sleep(0.5)
        encoder2.stop()
        
        # Verify that both cases work properly
        self.assertEqual(self.mock_byte_stream.push.call_count, 2)


# Add benchmark test class
class EncoderBenchmark:
    def __init__(self):
        # Create a real ByteStream for testing
        self.byte_stream_capacity = 50 * 1024 * 1024  # 50MB capacity
        self.byte_stream = ByteStream(capacity=self.byte_stream_capacity)
        
    def setup(self, n=100, k=70):
        """Prepare encoder and test data"""
        self.encoder = Encoder(self.byte_stream, n=n, k=k)
        
    def teardown(self):
        """Clean up the encoder"""
        if hasattr(self, 'encoder'):
            self.encoder.stop()
        # Create a new ByteStream object to replace reset
        self.byte_stream = ByteStream(capacity=self.byte_stream_capacity)
    
    def reset_byte_stream(self):
        """Helper method: Clear the buffer by creating a new ByteStream object"""
        self.byte_stream = ByteStream(capacity=self.byte_stream_capacity)
            
    def generate_test_data(self, size_kb):
        """Generate random test data of the specified size (in KB)"""
        size_bytes = size_kb * 1024
        # Ensure the data size is a multiple of k
        k = self.encoder.k
        size_bytes = size_bytes + (k - size_bytes % k) if size_bytes % k != 0 else size_bytes
        return bytes([random.randint(0, 255) for _ in range(size_bytes)])
    
    def benchmark_encoding_speed(self, sizes_kb=[10, 50, 100, 500, 1000]):
        """Test encoding speed for different data sizes"""
        print("\n===== Encoding Speed Benchmark =====")
        print(f"Encoding parameters: n={self.encoder.n}, k={self.encoder.k}")
        
        results = {}
        for size_kb in sizes_kb:
            test_data = self.generate_test_data(size_kb)
            data_size_mb = len(test_data) / (1024 * 1024)
            
            # Clear the ByteStream
            self.reset_byte_stream()
            
            # Warm-up - use synchronous encoding
            self.encoder.encode_sync(test_data)
            
            # Measure encoding time
            times = []
            for _ in range(3):  # Run 3 times and take the average
                self.reset_byte_stream()
                
                # Ensure we measure the complete encoding process
                start_time = time.time()
                success = self.encoder.encode_sync(test_data)
                end_time = time.time()
                
                if not success:
                    print(f"Warning: Encoding task may not have completed, results may be inaccurate")
                
                elapsed = end_time - start_time
                times.append(elapsed)
                
            avg_time = statistics.mean(times)
            throughput = data_size_mb / avg_time  # MB/s
            
            results[size_kb] = {
                'size_mb': data_size_mb,
                'avg_time': avg_time,
                'throughput': throughput
            }
            
            print(f"Data size: {size_kb} KB ({data_size_mb:.2f} MB)")
            print(f"Average encoding time: {avg_time:.4f} seconds")
            print(f"Throughput: {throughput:.2f} MB/s")
            print("----------------------------")
            
        return results
    
    def benchmark_different_parameters(self):
        """Test performance with different encoding parameters"""
        print("\n===== Different Encoding Parameters Benchmark =====")
        
        # Test different combinations of n and k values
        test_params = [
            (100, 50),   # High redundancy
            (100, 70),   # Medium redundancy
            (100, 90),   # Low redundancy
            (200, 100),  # Larger block size
            (50, 35),    # Smaller block size
        ]
        
        test_size_kb = 500  # Fixed test size of 500KB
        
        results = {}
        for n, k in test_params:
            # Reset the encoder
            self.teardown()
            self.setup(n=n, k=k)
            
            test_data = self.generate_test_data(test_size_kb)
            data_size_mb = len(test_data) / (1024 * 1024)
            
            # Clear the ByteStream
            self.reset_byte_stream()
            
            # Warm-up - use synchronous encoding
            self.encoder.encode_sync(test_data)
            
            # Measure encoding time
            times = []
            for _ in range(3):
                self.reset_byte_stream()
                
                # Ensure we measure the complete encoding process
                start_time = time.time()
                success = self.encoder.encode_sync(test_data)
                end_time = time.time()
                
                if not success:
                    print(f"Warning: Encoding task may not have completed, results may be inaccurate")
                
                elapsed = end_time - start_time
                times.append(elapsed)
                
            avg_time = statistics.mean(times)
            throughput = data_size_mb / avg_time  # MB/s
            
            results[(n, k)] = {
                'avg_time': avg_time,
                'throughput': throughput
            }
            
            print(f"Parameters: n={n}, k={k}, redundancy={(n-k)/n:.2f}")
            print(f"Data size: {test_size_kb} KB ({data_size_mb:.2f} MB)")
            print(f"Average encoding time: {avg_time:.4f} seconds")
            print(f"Throughput: {throughput:.2f} MB/s")
            print("----------------------------")
            
        return results
    
    def run_all_benchmarks(self):
        """Run all benchmark tests"""
        self.setup()
        
        try:
            print("\n========== FEC Encoder Performance Benchmark ==========")
            speed_results = self.benchmark_encoding_speed()
            param_results = self.benchmark_different_parameters()
            
            # Results summary
            print("\n========== Test Results Summary ==========")
            print("1. Throughput for different data sizes (MB/s):")
            for size_kb, result in speed_results.items():
                print(f"   - {size_kb} KB: {result['throughput']:.2f} MB/s")
                
            print("\n2. Throughput for different encoding parameters (MB/s):")
            for (n, k), result in param_results.items():
                print(f"   - n={n}, k={k}, redundancy={(n-k)/n:.2f}: {result['throughput']:.2f} MB/s")
                
        finally:
            self.teardown()


# If this file is run directly, execute benchmark tests
if __name__ == '__main__':
    # Uncomment the following to run benchmark tests separately
    # Run standard unit tests
    unittest.main()

    benchmark = EncoderBenchmark()
    benchmark.run_all_benchmarks()
    
