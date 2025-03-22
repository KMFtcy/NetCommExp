import unittest
import random
from src.mini_tcp.tcp_sender import TcpSender
from src.mini_tcp.tcp_message import TCPReceiverMessage, TCPSenderMessage
from src.mini_tcp.wrapping_intergers import Wrap32
from src.util.byte_stream import ByteStream
from src.mini_tcp.tcp_config import INITIAL_RTO

class TCPSenderTestHarness:
    def __init__(self, test_name: str, capacity: int = 4000):
        self.test_name = test_name
        self.input = ByteStream(capacity)
        self.isn = Wrap32(random.randint(0, 0xFFFFFFFF))
        self.sender = TcpSender(self.input, self.isn, INITIAL_RTO)
        self.segments_sent = []

        # Mock transmit function to capture sent segments
        def mock_transmit(segment: TCPSenderMessage) -> int:
            self.segments_sent.append(segment)
            return len(segment.payload) if segment.payload else 0

        from src.mini_tcp.transmit_func import set_transmit_func_call
        set_transmit_func_call(mock_transmit)

    def push(self, data: str = "") -> None:
        """Push data to the sender's input stream"""
        if data:
            self.input.push(data.encode())
        self.sender.push()

    def expect_message(self, *, no_flags: bool = True, syn: bool = False,
                    data: str = "", payload_size: int = None, seqno: Wrap32 = None) -> None:
        """Verify that the next message matches expectations"""
        if not self.segments_sent:
            raise AssertionError(f"{self.test_name}: Expected a segment but none were sent!")

        seg = self.segments_sent.pop(0)

        if no_flags:
            assert not seg.SYN and not seg.FIN, f"{self.test_name}: Expected no flags but got SYN={seg.SYN}, FIN={seg.FIN}"

        if syn:
            assert seg.SYN, f"{self.test_name}: Expected SYN flag but didn't get it"

        if data:
            assert seg.payload == data.encode(), f"{self.test_name}: Expected data '{data}' but got '{seg.payload.decode()}'"

        if payload_size is not None:
            actual_size = len(seg.payload) if seg.payload else 0
            assert actual_size == payload_size, f"{self.test_name}: Expected payload size {payload_size} but got {actual_size}"

        if seqno is not None:
            assert seg.seqno == seqno, f"{self.test_name}: Expected seqno {seqno} but got {seg.seqno}"

    def expect_no_segment(self) -> None:
        """Verify that no segments were sent"""
        assert not self.segments_sent, f"{self.test_name}: Expected no segments but got {len(self.segments_sent)}"

    def receive_ack(self, ackno: Wrap32, window_size: int = 1000) -> None:
        """Simulate receiving an ACK from the receiver"""
        msg = TCPReceiverMessage(ackno=ackno, window_size=window_size)
        self.sender.receive(msg)

    def has_error(self) -> bool:
        """Check if the sender has an error"""
        return self.input.has_error()

class TestTCPSender(unittest.TestCase):
    def test_repeat_ack_ignored(self):
        """Test that repeated ACKs are ignored"""
        test = TCPSenderTestHarness("Repeat ACK is ignored")

        # Initial SYN
        test.push()
        test.expect_message(no_flags=False, syn=True, payload_size=0, seqno=test.isn)
        test.expect_no_segment()

        # Receive ACK for SYN
        test.receive_ack(Wrap32(test.isn.raw_value + 1))

        # Send some data
        test.push("a")
        test.expect_message(data="a")
        test.expect_no_segment()

        # Receive same ACK again - should be ignored
        test.receive_ack(Wrap32(test.isn.raw_value + 1))
        test.expect_no_segment()

        self.assertFalse(test.has_error())

    def test_old_ack_ignored(self):
        """Test that old ACKs are ignored"""
        test = TCPSenderTestHarness("Old ACK is ignored")

        # Initial SYN
        test.push()
        test.expect_message(no_flags=False, syn=True, payload_size=0, seqno=test.isn)
        test.expect_no_segment()

        # Receive ACK for SYN
        test.receive_ack(Wrap32(test.isn.raw_value + 1))

        # Send first data segment
        test.push("a")
        test.expect_message(data="a")
        test.expect_no_segment()

        # Receive ACK for first data
        test.receive_ack(Wrap32(test.isn.raw_value + 2))
        test.expect_no_segment()

        # Send second data segment
        test.push("b")
        test.expect_message(data="b")
        test.expect_no_segment()

        # Receive old ACK - should be ignored
        test.receive_ack(Wrap32(test.isn.raw_value + 1))
        test.expect_no_segment()

        self.assertFalse(test.has_error())

    def test_impossible_ackno_ignored(self):
        """Test that impossible ACKs (beyond next seqno) are ignored"""
        test = TCPSenderTestHarness("Impossible ackno (beyond next seqno) is ignored")

        # Initial SYN
        test.push()
        test.expect_message(no_flags=False, syn=True, payload_size=0, seqno=test.isn)

        # Check bytes in flight
        self.assertEqual(len(test.sender.outstanding_data), 1)

        # Receive impossible ACK
        test.receive_ack(Wrap32(test.isn.raw_value + 2), window_size=1000)

        # Should still have the same bytes in flight
        self.assertEqual(len(test.sender.outstanding_data), 1)

        self.assertFalse(test.has_error())

if __name__ == '__main__':
    unittest.main()