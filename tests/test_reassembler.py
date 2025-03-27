import unittest
from src.util.byte_stream import ByteStream
from src.mini_tcp.reassembler import Reassembler
import time

class ReassemblerTestHarness:
    def __init__(self, test_name: str, capacity: int = 65535):
        self.test_name = test_name
        self.output = ByteStream(capacity)
        self.reassembler = Reassembler(self.output)

    def insert(self, first_index: int, data: str, is_last: bool = False) -> None:
        """Insert data into the reassembler"""
        self.reassembler.insert(first_index, data.encode(), is_last)

    def expect_bytes_buffered(self, expected: int) -> None:
        """Verify the number of bytes buffered in the output stream"""
        actual = self.output.bytes_buffered()
        assert actual == expected, \
            f"{self.test_name}: Expected {expected} bytes buffered but got {actual}"

    def expect_bytes_pending(self, expected: int) -> None:
        """Verify the number of bytes pending in the reassembler"""
        actual = self.reassembler.count_bytes_pending()
        assert actual == expected, \
            f"{self.test_name}: Expected {expected} bytes pending but got {actual}"

    def expect_output(self, expected: str) -> None:
        """Verify the output data matches expectations"""
        length = len(expected)
        actual = self.output.pop(length)
        assert actual == expected.encode(), \
            f"{self.test_name}: Expected output '{expected}' but got '{actual.decode()}'"

    def expect_eof(self, expected: bool = True) -> None:
        """Verify the EOF state of the output stream"""
        actual = self.output.is_closed()
        assert actual == expected, \
            f"{self.test_name}: Expected EOF to be {expected} but got {actual}"

    def expect_error(self) -> bool:
        """Check if the output stream has an error"""
        return self.output.has_error()

class TestReassembler(unittest.TestCase):
    def test_insert_in_order(self):
        """Test inserting data in order"""
        test = ReassemblerTestHarness("Insert in order")
        
        # Insert single segment
        test.insert(0, "hello")
        test.expect_bytes_buffered(5)
        test.expect_bytes_pending(0)
        test.expect_output("hello")
        test.expect_eof(False)
        self.assertFalse(test.expect_error())

    def test_insert_out_of_order(self):
        """Test inserting data out of order"""
        test = ReassemblerTestHarness("Insert out of order")
        
        # Insert out of order segment
        test.insert(5, "world")
        test.expect_bytes_buffered(0)
        test.expect_bytes_pending(5)
        
        # Insert in order segment
        test.insert(0, "hello")
        test.expect_bytes_buffered(10)
        test.expect_bytes_pending(0)
        test.expect_output("helloworld")
        test.expect_eof(False)
        self.assertFalse(test.expect_error())

    def test_insert_with_eof(self):
        """Test inserting data with EOF flag"""
        test = ReassemblerTestHarness("Insert with EOF")
        
        test.insert(0, "hello", True)
        test.expect_bytes_buffered(5)
        test.expect_bytes_pending(0)
        test.expect_output("hello")
        test.expect_eof(True)
        self.assertFalse(test.expect_error())

    def test_overlapping_segments(self):
        """Test handling of overlapping segments"""
        test = ReassemblerTestHarness("Overlapping segments")
        
        # Insert overlapping segments
        test.insert(0, "hello")
        test.insert(3, "loworld")
        test.expect_bytes_buffered(10)
        test.expect_bytes_pending(0)
        test.expect_output("helloworld")
        self.assertFalse(test.expect_error())

    def test_duplicate_segments(self):
        """Test handling of duplicate segments"""
        test = ReassemblerTestHarness("Duplicate segments")
        
        # Insert original segment
        test.insert(0, "hello")
        test.expect_bytes_buffered(5)
        test.expect_output("hello")
        
        # Insert duplicate segment
        test.insert(0, "hello")
        test.expect_bytes_buffered(0)
        test.expect_bytes_pending(0)
        self.assertFalse(test.expect_error())

    def test_multiple_gaps(self):
        """Test handling of multiple gaps in data"""
        test = ReassemblerTestHarness("Multiple gaps", 100)
        
        # Insert segments with gaps
        test.insert(0, "hello")
        test.insert(10, "world")
        test.insert(20, "!")
        test.expect_bytes_buffered(5)
        test.expect_bytes_pending(6)
        test.expect_output("hello")
        
        # Fill the gaps
        test.insert(5, "brave")
        test.expect_bytes_buffered(10)
        test.expect_bytes_pending(1)
        test.expect_output("braveworld")
        test.insert(15, "new")
        test.expect_bytes_buffered(3)
        test.expect_bytes_pending(1)
        test.expect_output("new")
        test.insert(18, "!!")
        test.expect_bytes_buffered(3)
        test.expect_bytes_pending(0)
        test.expect_output("!!!")
        self.assertFalse(test.expect_error())

    def test_capacity_limits(self):
        """Test respecting capacity limits"""
        test = ReassemblerTestHarness("Capacity limits", capacity=10)
        
        # Try to insert more than capacity
        test.insert(0, "hello")
        test.insert(5, "worldextra")
        test.expect_bytes_buffered(10)
        test.expect_bytes_pending(0)
        test.expect_output("helloworld")
        self.assertFalse(test.expect_error())

    def test_out_of_order_with_capacity(self):
        """Test out of order insertion with capacity constraints"""
        test = ReassemblerTestHarness("Out of order with capacity", capacity=15)
        
        # Insert segments out of order with capacity constraint
        test.insert(5, "world")
        test.expect_bytes_pending(5)
        test.insert(0, "hello")
        test.expect_bytes_buffered(10)
        test.expect_bytes_pending(0)
        test.expect_output("helloworld")
        self.assertFalse(test.expect_error())

    def test_eof_with_pending(self):
        """Test EOF handling with pending data"""
        test = ReassemblerTestHarness("EOF with pending data")
        
        # Insert segments with EOF but missing data
        test.insert(5, "world", True)
        test.expect_bytes_buffered(0)
        test.expect_bytes_pending(5)
        test.expect_eof(False)
        
        # Insert missing data
        test.insert(0, "hello")
        test.expect_bytes_buffered(10)
        test.expect_bytes_pending(0)
        test.expect_output("helloworld")
        test.expect_eof(True)
        self.assertFalse(test.expect_error())

class TestReassemblerPerformance(unittest.TestCase):
    def measure_throughput(self, packet_size: int, num_operations: int, out_of_order: bool = False) -> float:
        """Measure reassembler throughput under different conditions"""
        test = ReassemblerTestHarness("Performance test", packet_size * num_operations)
        
        # Prepare test data
        test_data = 'a' * packet_size
        total_bytes = packet_size * num_operations
        
        # Measure insert performance
        start_time = time.time()
        
        if out_of_order:
            # Insert packets in reverse order
            for i in range(num_operations - 1, -1, -1):
                test.insert(i * packet_size, test_data)
        else:
            # Insert packets in order
            for i in range(num_operations):
                test.insert(i * packet_size, test_data)
        
        duration = time.time() - start_time
        throughput = total_bytes / duration  # bytes per second
        
        return throughput

    def test_throughput_performance(self):
        """Test reassembler throughput performance"""
        # Test parameters
        packet_sizes = [4096, 1024, 512, 256, 128, 64, 32]  # bytes
        operations = 100  # number of insert operations for each test
        
        print("\nReassembler Throughput Test")
        print("=" * 70)
        print(f"Operations per test: {operations}")
        print("-" * 70)
        print("Packet Size | In-Order Throughput | Out-of-Order Throughput")
        print("-" * 70)
        
        for packet_size in packet_sizes:
            # Measure throughput for both in-order and out-of-order scenarios
            in_order_throughput = self.measure_throughput(packet_size, operations, False)
            out_of_order_throughput = self.measure_throughput(packet_size, operations, True)
            
            # Convert to MB/s for display
            in_order_mb = in_order_throughput / (1024 * 1024)
            out_of_order_mb = out_of_order_throughput / (1024 * 1024)
            
            print(f"{packet_size:^11d} | {in_order_mb:^18.2f} | {out_of_order_mb:^20.2f} MB/s")
        
        print("-" * 70)

if __name__ == "__main__":
    unittest.main(verbosity=2) 