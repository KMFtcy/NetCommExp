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

    def push(self, data: str = "", close: bool = False) -> None:
        """Push data to the sender's input stream"""
        if data:
            self.input.push(data.encode())
        if close:
            self.input.close()
        self.sender.push()

    def expect_message(self, *, no_flags: bool = True, syn: bool = False, fin: bool = False,
                      data: str = "", payload_size: int = None, seqno: Wrap32 = None) -> None:
        """Verify that the next message matches expectations"""
        if not self.segments_sent:
            raise AssertionError(f"{self.test_name}: Expected a segment but none were sent!")

        seg = self.segments_sent.pop(0)

        if no_flags:
            assert not seg.SYN and not seg.FIN, f"{self.test_name}: Expected no flags but got SYN={seg.SYN}, FIN={seg.FIN}"

        if syn:
            assert seg.SYN, f"{self.test_name}: Expected SYN flag but didn't get it"

        if fin:
            assert seg.FIN, f"{self.test_name}: Expected FIN flag but didn't get it"

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

    def expect_seqno(self, seqno: Wrap32) -> None:
        """Verify the next sequence number through empty segments"""
        empty_segments = self.sender.make_empty_message()
        assert empty_segments.seqno == seqno, \
            f"{self.test_name}: Expected next seqno {seqno} but got {empty_segments.seqno}"

    def expect_seqnos_in_flight(self, n: int) -> None:
        """Verify the number of sequence numbers in flight"""
        assert min(self.sender.next_seqno, self.sender.fin_seqno) - self.sender.ack_seqno == n, \
            f"{self.test_name}: Expected {n} seqnos in flight but got {min(self.sender.next_seqno, self.sender.fin_seqno) - self.sender.ack_seqno}"

    def close(self) -> None:
        """Close the input stream"""
        self.input.close()
        self.sender.push()

    def tick(self, ms: int) -> None:
        """Advance time by the specified number of milliseconds"""
        self.sender.tick(ms)

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
        test.expect_seqnos_in_flight(1)

        # Receive impossible ACK
        test.receive_ack(Wrap32(test.isn.raw_value + 2), window_size=1000)

        # Should still have the same bytes in flight
        test.expect_seqnos_in_flight(1)

        self.assertFalse(test.has_error())

    def test_fin_sent(self):
        """Test sending FIN flag"""
        test = TCPSenderTestHarness("FIN sent test")

        # Initial SYN
        test.push()
        test.expect_message(no_flags=False, syn=True, payload_size=0, seqno=test.isn)

        # Receive ACK for SYN
        test.receive_ack(Wrap32(test.isn.raw_value + 1))
        test.expect_seqno(test.isn + 1)
        test.expect_seqnos_in_flight(0)

        # Close the stream
        test.close()
        test.expect_message(no_flags=False, fin=True, seqno=test.isn + 1)
        test.expect_seqno(test.isn + 2)
        test.expect_seqnos_in_flight(1)
        test.expect_no_segment()

        self.assertFalse(test.has_error())

    def test_fin_with_data(self):
        """Test sending FIN with data"""
        test = TCPSenderTestHarness("FIN with data")

        # Initial SYN
        test.push()
        test.expect_message(no_flags=False, syn=True, payload_size=0, seqno=test.isn)

        # Receive ACK for SYN
        test.receive_ack(Wrap32(test.isn.raw_value + 1))
        test.expect_seqno(test.isn + 1)
        test.expect_seqnos_in_flight(0)

        # Push data and close
        test.push("hello", close=True)
        test.expect_message(no_flags=False, fin=True, seqno=test.isn + 1, data="hello")
        test.expect_seqno(test.isn + 7)  # ISN + 1 (SYN) + 5 (data) + 1 (FIN)
        test.expect_seqnos_in_flight(6)  # 5 (data) + 1 (FIN)
        test.expect_no_segment()

    def test_syn_fin(self):
        """Test sending SYN and FIN together"""
        test = TCPSenderTestHarness("SYN + FIN")

        # Set window size without pushing
        test.receive_ack(None, window_size=1024)

        # Close immediately
        test.close()
        test.expect_message(no_flags=False, syn=True, fin=True, payload_size=0, seqno=test.isn)
        test.expect_seqno(test.isn + 2)
        test.expect_seqnos_in_flight(2)
        test.expect_no_segment()

        self.assertFalse(test.has_error())

    def test_fin_acked(self):
        """Test FIN being acknowledged"""
        test = TCPSenderTestHarness("FIN acked test")

        # Initial SYN
        test.push()
        test.expect_message(no_flags=False, syn=True, payload_size=0, seqno=test.isn)

        # Receive ACK for SYN
        test.receive_ack(Wrap32(test.isn.raw_value + 1))
        test.expect_seqno(test.isn + 1)
        test.expect_seqnos_in_flight(0)

        # Close and send FIN
        test.close()
        test.expect_message(no_flags=False, fin=True, seqno=test.isn + 1)
        test.expect_seqnos_in_flight(1)

        # Receive ACK for FIN
        test.receive_ack(Wrap32(test.isn.raw_value + 2))
        test.expect_seqno(test.isn + 2)
        test.expect_seqnos_in_flight(0)
        test.expect_no_segment()

        self.assertFalse(test.has_error())

    def test_fin_not_acked(self):
        """Test unacknowledged FIN"""
        test = TCPSenderTestHarness("FIN not acked test")

        # Initial SYN
        test.push()
        test.expect_message(no_flags=False, syn=True, payload_size=0, seqno=test.isn)

        # Receive ACK for SYN
        test.receive_ack(Wrap32(test.isn.raw_value + 1))
        test.expect_seqno(test.isn + 1)
        test.expect_seqnos_in_flight(0)

        # Close and send FIN
        test.close()
        test.expect_message(no_flags=False, fin=True, seqno=test.isn + 1)
        test.expect_seqno(test.isn + 2)
        test.expect_seqnos_in_flight(1)

        # Receive old ACK (not acknowledging FIN)
        test.receive_ack(Wrap32(test.isn.raw_value + 1))
        test.expect_seqno(test.isn + 2)
        test.expect_seqnos_in_flight(1)
        test.expect_no_segment()

    def test_fin_retx(self):
        """Test FIN retransmission"""
        test = TCPSenderTestHarness("FIN retx test")

        # Initial SYN
        test.push()
        test.expect_message(no_flags=False, syn=True, payload_size=0, seqno=test.isn)

        # Receive ACK for SYN
        test.receive_ack(Wrap32(test.isn.raw_value + 1))
        test.expect_seqno(test.isn + 1)
        test.expect_seqnos_in_flight(0)

        # Close and send FIN
        test.close()
        test.expect_message(no_flags=False, fin=True, seqno=test.isn + 1)
        test.expect_seqno(test.isn + 2)
        test.expect_seqnos_in_flight(1)

        # Receive old ACK (not acknowledging FIN)
        test.receive_ack(Wrap32(test.isn.raw_value + 1))
        test.expect_seqno(test.isn + 2)
        test.expect_seqnos_in_flight(1)
        test.expect_no_segment()

        # Wait just before timeout
        test.tick(INITIAL_RTO - 1)
        test.expect_seqno(test.isn + 2)
        test.expect_seqnos_in_flight(1)
        test.expect_no_segment()

        # Timeout occurs
        test.tick(1)
        test.expect_message(no_flags=False, fin=True, seqno=test.isn + 1)
        test.expect_seqno(test.isn + 2)
        test.expect_seqnos_in_flight(1)
        test.expect_no_segment()

        # Additional tick
        test.tick(1)
        test.expect_seqno(test.isn + 2)
        test.expect_seqnos_in_flight(1)
        test.expect_no_segment()

        # Finally receive ACK for FIN
        test.receive_ack(Wrap32(test.isn.raw_value + 2))
        test.expect_seqnos_in_flight(0)
        test.expect_seqno(test.isn + 2)
        test.expect_no_segment()

        self.assertFalse(test.has_error())

if __name__ == '__main__':
    unittest.main()