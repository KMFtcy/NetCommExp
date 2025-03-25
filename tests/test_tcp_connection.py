import unittest
import random
from src.mini_tcp.tcp_connection import TCPConnection
from src.mini_tcp.tcp_message import TCPMessage, TCPSenderMessage, TCPReceiverMessage
from src.mini_tcp.wrapping_intergers import Wrap32
from src.mini_tcp.tcp_config import TCPConfig, MAX_WINDOW_SIZE, INITIAL_RTO

class TCPConnectionTestHarness:
    def __init__(self, test_name: str, window_size: int = MAX_WINDOW_SIZE, rto: int = INITIAL_RTO, isn: Wrap32 = Wrap32(0)):
        self.test_name = test_name
        config = TCPConfig(
            window_size=window_size,
            rto=rto,
            isn=isn
        )
        self.connection = TCPConnection(config)
        self.segments_received = []
        
        def mock_transmit(segment: TCPMessage) -> None:
            self.segments_received.append(segment)
            
        self.mock_transmit = mock_transmit
        
    def push(self, data: str = "", close: bool = False) -> None:
        """Push data to the connection's outbound stream"""
        if data:
            self.connection.outbound_stream.push(data.encode())
        if close:
            self.connection.outbound_stream.close()
        self.connection.push(self.mock_transmit)
    
    def receive(self, data: str = "", syn: bool = False, fin: bool = False, 
                seqno: Wrap32 = None, ackno: Wrap32 = None, window_size: int = MAX_WINDOW_SIZE) -> None:
        """Simulate receiving a segment from the network"""
        sender_msg = TCPSenderMessage(
            SYN=syn,
            FIN=fin,
            seqno=seqno if seqno else Wrap32(0),
            payload=data.encode() if data else b""
        )
        receiver_msg = TCPReceiverMessage(
            ackno=ackno,
            window_size=window_size
        )
        msg = TCPMessage(sender_msg, receiver_msg)
        self.connection.receive(msg, self.mock_transmit)
    
    def expect_data(self, data: str = None, syn: bool = False, fin: bool = False, seqno: Wrap32 = None, ackno: Wrap32 = None) -> None:
        """Verify that the next message contains expected data and flags"""
        if not self.segments_received:
            raise AssertionError(f"{self.test_name}: Expected a segment but none were sent!")
            
        seg = self.segments_received.pop(0)
        
        if syn:
            assert seg.sender_message.SYN, f"{self.test_name}: Expected SYN flag but didn't get it"
            
        if fin:
            assert seg.sender_message.FIN, f"{self.test_name}: Expected FIN flag but didn't get it"
            
        if data is not None:
            actual_data = seg.sender_message.payload.decode() if seg.sender_message.payload else ""
            assert actual_data == data, \
                f"{self.test_name}: Expected data '{data}' but got '{actual_data}'"

        if ackno is not None:
            assert seg.receiver_message.ackno == ackno, \
                f"{self.test_name}: Expected ackno '{ackno}' but got '{seg.receiver_message.ackno}'"

        if seqno is not None:
            assert seg.sender_message.seqno == seqno, \
                f"{self.test_name}: Expected seqno '{seqno}' but got '{seg.sender_message.seqno}'"
    
    def expect_no_data(self) -> None:
        """Verify that no segments were sent"""
        assert not self.segments_received, \
            f"{self.test_name}: Expected no segments but got {len(self.segments_received)}"
    
    def tick(self, ms: int) -> None:
        """Advance time by the specified number of milliseconds"""
        self.connection.tick(ms)

class TestTCPConnection(unittest.TestCase):
    def test_basic_connect_as_client(self):
        """Test basic connection establishment"""
        test = TCPConnectionTestHarness("Basic connect", isn=Wrap32(45535))
        
        # Initial SYN
        test.push()
        test.expect_data(syn=True)
        test.expect_no_data()
        
        # Receive SYN+ACK
        test.receive(seqno=Wrap32(65535), syn=True, ackno=Wrap32(1))
        test.expect_data(seqno=Wrap32(45536), ackno=Wrap32(65536))
        test.expect_no_data()
        
        self.assertTrue(test.connection.active())

    def test_connect_syn_with_data_as_client(self):
        pass
    
    # def test_custom_window_size(self):
    #     """Test connection with custom window size"""
    #     custom_window = 1000
    #     test = TCPConnectionTestHarness("Custom window size", window_size=custom_window)
        
    #     # Initial SYN
    #     test.push()
    #     test.expect_data(syn=True)
        
    #     # Receive SYN+ACK with matching window size
    #     test.receive(syn=True, ackno=Wrap32(1), window_size=custom_window)
    #     test.expect_data()
        
    #     # Try to send more than window size
    #     test.push("a" * (custom_window + 100))
    #     test.expect_data(data="a" * custom_window)
    #     test.expect_no_data()
    
    # def test_custom_rto(self):
    #     """Test connection with custom RTO"""
    #     custom_rto = 2000
    #     test = TCPConnectionTestHarness("Custom RTO", rto=custom_rto)
        
    #     # Initial SYN
    #     test.push()
    #     test.expect_data(syn=True)
        
    #     # Wait just before RTO
    #     test.tick(custom_rto - 1)
    #     test.expect_no_data()
        
    #     # Wait for RTO to trigger retransmission
    #     test.tick(1)
    #     test.expect_data(syn=True)
    
    # def test_window_management(self):
    #     """Test window size management with config"""
    #     small_window = 10
    #     test = TCPConnectionTestHarness("Window management", window_size=small_window)
        
    #     # Establish connection
    #     test.push()
    #     test.expect_data(syn=True)
    #     test.receive(syn=True, ackno=Wrap32(1), window_size=small_window)
    #     test.expect_data()
        
    #     # Try to send more data than window allows
    #     test.push("Hello World!")  # 12 bytes
    #     test.expect_data(data="Hello Worl")  # Only 10 bytes should be sent
    #     test.expect_no_data()
        
    #     # Acknowledge first segment and increase window
    #     test.receive(ackno=Wrap32(11), window_size=20)
    #     test.expect_data(data="d!")  # Remaining data should be sent
    #     test.expect_no_data()

if __name__ == '__main__':
    unittest.main()
