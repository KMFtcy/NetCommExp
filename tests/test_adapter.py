import unittest
import socket
from unittest.mock import Mock, patch
from src.mini_tcp.adapter import TCPOverUDPAdapter
from src.mini_tcp.tcp_message import TCPMessage, TCPSenderMessage, TCPReceiverMessage
from src.mini_tcp.wrapping_intergers import Wrap32
import time

class TestUDPAdapter(unittest.TestCase):
    def setUp(self):
        """Set up the test environment before each test case"""
        self.mock_socket = Mock(spec=socket.socket)
        self.adapter = TCPOverUDPAdapter(self.mock_socket)
        
        # Create a test TCP message
        self.test_message = TCPMessage(
            sender_message=TCPSenderMessage(
                seqno=Wrap32(12345),
                payload=b"Hello, World!",
                SYN=True,
                FIN=False,
                RST=False
            ),
            receiver_message=TCPReceiverMessage(
                ackno=Wrap32(67890),
                window_size=1000,
                RST=False
            )
        )

    def test_serialize_deserialize(self):
        """Test serialization and deserialization functionality"""
        # Serialize the message
        serialized_data = self.adapter.serialize_tcp_message(self.test_message)
        
        # Deserialize the message
        deserialized_message = self.adapter.deserialize_tcp_message(serialized_data)
        
        # Verify that all fields match after serialization and deserialization
        self.assertEqual(
            self.test_message.sender_message.seqno.raw_value,
            deserialized_message.sender_message.seqno.raw_value
        )
        self.assertEqual(
            self.test_message.sender_message.payload,
            deserialized_message.sender_message.payload
        )
        self.assertEqual(
            self.test_message.sender_message.SYN,
            deserialized_message.sender_message.SYN
        )
        self.assertEqual(
            self.test_message.receiver_message.ackno.raw_value,
            deserialized_message.receiver_message.ackno.raw_value
        )
        self.assertEqual(
            self.test_message.receiver_message.window_size,
            deserialized_message.receiver_message.window_size
        )

    def test_write(self):
        """Test write functionality"""
        address = ("localhost", 12345)
        
        # Call write method
        self.adapter.write(self.test_message, address)
        
        # Verify that socket.sendto was called correctly
        self.mock_socket.sendto.assert_called_once()
        call_args = self.mock_socket.sendto.call_args
        self.assertEqual(call_args[0][1], address)  # Verify address
        
        # Verify the length of sent data
        sent_data = call_args[0][0]
        self.assertEqual(len(sent_data), 14 + len(self.test_message.sender_message.payload))

    def test_read(self):
        """Test read functionality"""
        test_address = ("127.0.0.1", 8080)
        
        # Mock receiving data
        serialized_data = self.adapter.serialize_tcp_message(self.test_message)
        self.mock_socket.recvfrom.return_value = (serialized_data, test_address)
        
        # Call read method
        received_message, addr = self.adapter.read()
        
        # Verify received message
        self.assertEqual(addr, test_address)
        self.assertEqual(
            received_message.sender_message.seqno.raw_value,
            self.test_message.sender_message.seqno.raw_value
        )
        self.assertEqual(
            received_message.sender_message.payload,
            self.test_message.sender_message.payload
        )

    def test_read_error(self):
        """Test error handling during read operation"""
        # Mock socket error
        self.mock_socket.recvfrom.side_effect = socket.error()
        
        # Call read method
        message, addr = self.adapter.read()
        
        # Verify return values
        self.assertIsNone(message)
        self.assertIsNone(addr)

    def test_empty_message(self):
        """Test handling of empty messages"""
        empty_message = TCPMessage(
            sender_message=TCPSenderMessage(),
            receiver_message=TCPReceiverMessage()
        )
        
        # Test serialization and deserialization of empty message
        serialized_data = self.adapter.serialize_tcp_message(empty_message)
        deserialized_message = self.adapter.deserialize_tcp_message(serialized_data)
        
        # Verify results
        self.assertIsNone(deserialized_message.sender_message.seqno)
        self.assertIsNone(deserialized_message.sender_message.payload)
        self.assertIsNone(deserialized_message.receiver_message.ackno)
        self.assertEqual(deserialized_message.receiver_message.window_size, 0)

class TestUDPAdapterPerformance(unittest.TestCase):
    def setUp(self):
        """Set up the test environment before each test case"""
        self.mock_socket = Mock(spec=socket.socket)
        self.adapter = TCPOverUDPAdapter(self.mock_socket)

    def measure_throughput(self, payload_size: int, num_packets: int) -> tuple[float, float]:
        # Create test message with specified payload size
        test_message = TCPMessage(
            sender_message=TCPSenderMessage(
                seqno=Wrap32(12345),
                payload=b"X" * payload_size,
                SYN=False,
                FIN=False,
                RST=False
            ),
            receiver_message=TCPReceiverMessage(
                ackno=Wrap32(67890),
                window_size=1000,
                RST=False
            )
        )

        # Measure serialization performance
        start_time = time.time()
        for _ in range(num_packets):
            serialized_data = self.adapter.serialize_tcp_message(test_message)
        serialize_time = time.time() - start_time
        
        # Measure deserialization performance
        start_time = time.time()
        for _ in range(num_packets):
            _ = self.adapter.deserialize_tcp_message(serialized_data)
        deserialize_time = time.time() - start_time

        # Calculate throughput (bytes/second)
        total_bytes = len(serialized_data) * num_packets
        serialize_throughput = total_bytes / serialize_time
        deserialize_throughput = total_bytes / deserialize_time

        return serialize_throughput, deserialize_throughput

    def test_throughput_performance(self):
        # Test parameters
        payload_sizes = [4096, 1024, 512, 256, 128, 64, 32]  # bytes
        num_packets = 1000  # number of packets for each test

        print("\nUDP Adapter Throughput Test")
        print("=" * 80)
        print(f"Packets per test: {num_packets}")
        print("-" * 80)
        print("Payload Size | Total Size | Serialization Throughput | Deserialization Throughput")
        print("-" * 80)

        for payload_size in payload_sizes:
            # Get throughput measurements
            serialize_throughput, deserialize_throughput = self.measure_throughput(payload_size, num_packets)
            
            # Calculate total message size (payload + header)
            total_size = payload_size + 14  # 14 bytes for header

            # Convert to MB/s for display
            serialize_mb = serialize_throughput / (1024 * 1024)
            deserialize_mb = deserialize_throughput / (1024 * 1024)

            print(f"{payload_size:^11d} | {total_size:^10d} | {serialize_mb:^22.2f} | {deserialize_mb:^23.2f} MB/s")

            # Optional: Assert minimum performance requirements
            # min_throughput = 5 * 1024 * 1024  # 5 MB/s in bytes/s
            # self.assertGreater(
            #     serialize_throughput,
            #     min_throughput,
            #     f"Serialization throughput too low for {payload_size} byte payloads"
            # )
            # self.assertGreater(
            #     deserialize_throughput,
            #     min_throughput,
            #     f"Deserialization throughput too low for {payload_size} byte payloads"
            # )

        print("-" * 80)

if __name__ == '__main__':
    unittest.main() 