import unittest
from src.util.byte_stream import ByteStream
from src.mini_tcp.reassembler import Reassembler
import time

class TestReassembler(unittest.TestCase):
    def setUp(self):
        self.output = ByteStream(100000)
        self.reassembler = Reassembler(self.output)

    def test_insert_in_order(self):
        data = b"hello"
        self.reassembler.insert(0, data, False)
        self.assertEqual(self.output.bytes_buffered(), len(data))
        self.assertEqual(self.output.pop(len(data)), data)

    def test_insert_out_of_order(self):
        data1 = b"world"
        data2 = b"hello"
        self.reassembler.insert(5, data1, False)  # Out of order
        self.assertEqual(self.output.bytes_buffered(), 0)  # Should not be added but buffed in reassembler
        self.assertEqual(self.reassembler.count_bytes_pending(), len(data1))
        self.reassembler.insert(0, data2, False)  # In order
        self.assertEqual(self.reassembler.count_bytes_pending(), 0)
        self.assertEqual(self.output.bytes_buffered(), len(data2) + len(data1)) # Should be added all buffer to output
        self.assertEqual(self.output.pop(len(data2) + len(data1)), data2 + data1)

    def test_insert_with_eof(self):
        data = b"hello"
        self.reassembler.insert(0, data, True)
        self.assertTrue(self.output.is_closed())
        self.assertEqual(self.output.bytes_buffered(), len(data))
        self.assertEqual(self.output.pop(len(data)), data)

    def test_insert_out_of_order_no_effect(self):
        data = b"world"
        self.reassembler.insert(5, data, False)  # Out of order
        self.assertEqual(self.output.bytes_buffered(), 0)  # Should not be added

    def test_insert_in_order_with_eof(self):
        data = b"hello"
        self.reassembler.insert(0, data, True)
        self.assertTrue(self.output.is_closed())
        self.assertEqual(self.output.bytes_buffered(), len(data))
        self.assertEqual(self.output.pop(len(data)), data)

    def test_correctness_of_output(self):
        data1 = b"hello"
        data2 = b"world"
        self.reassembler.insert(0, data1, False)  # In order
        self.reassembler.insert(5, data2, False)  # In order
        expected_output = data1 + data2
        self.assertEqual(self.output.bytes_buffered(), len(expected_output))
        self.assertEqual(self.output.pop(len(expected_output)), expected_output)

class TestReassemblerPerformance(unittest.TestCase):
    def measure_throughput(self, packet_size: int, num_operations: int, out_of_order: bool = False) -> float:
        # Create fresh instances for each test
        output = ByteStream(packet_size * num_operations)
        reassembler = Reassembler(output)
        
        # Prepare test data
        test_data = bytes([i % 256 for i in range(packet_size)])
        total_bytes = packet_size * num_operations

        # Measure insert performance
        start_time = time.time()
        
        if out_of_order:
            # Insert packets in reverse order to test out-of-order handling
            for i in range(num_operations - 1, -1, -1):
                reassembler.insert(i * packet_size, test_data, i == 0)
        else:
            # Insert packets in order
            for i in range(num_operations):
                reassembler.insert(i * packet_size, test_data, i == num_operations - 1)
        
        duration = time.time() - start_time
        throughput = total_bytes / duration  # bytes per second

        return throughput

    def test_throughput_performance(self):
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

            # Assert minimum performance requirements
            # min_throughput = 5 * 1024 * 1024  # 5 MB/s in bytes/s
            # self.assertGreater(
            #     in_order_throughput, 
            #     min_throughput, 
            #     f"In-order throughput too low for {packet_size} byte packets"
            # )
            # self.assertGreater(
            #     out_of_order_throughput, 
            #     min_throughput, 
            #     f"Out-of-order throughput too low for {packet_size} byte packets"
            # )

        print("-" * 70)

if __name__ == "__main__":
    unittest.main(verbosity=2) 