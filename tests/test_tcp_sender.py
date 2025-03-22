import unittest
import random
from src.mini_tcp.tcp_sender import TcpSender
from src.mini_tcp.tcp_message import TCPReceiverMessage, TCPSenderMessage
from src.mini_tcp.wrapping_intergers import Wrap32
from src.util.byte_stream import ByteStream
from src.mini_tcp.tcp_config import INITIAL_RTO, MAX_RETX_ATTEMPTS

class TCPSenderTestHarness:
    def __init__(self, test_name: str, capacity: int = 4000, retx_timeout: int = INITIAL_RTO):
        self.test_name = test_name
        self.input = ByteStream(capacity)
        self.isn = Wrap32(random.randint(0, 0xFFFFFFFF))
        self.sender = TcpSender(self.input, self.isn, retx_timeout)
        self.segments_sent = []
        self.max_retx_exceeded = False
        
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
    
    def expect_consecutive_retransmissions(self, n: int) -> None:
        """Verify the number of consecutive retransmissions"""
        assert self.sender.retrans_count == n, \
            f"{self.test_name}: Expected {n} consecutive retransmissions but got {self.sender.retrans_count}"
    
    def close(self) -> None:
        """Close the input stream"""
        self.input.close()
        self.sender.push()
    
    def tick(self, ms: int, expect_max_retx_exceeded: bool = False) -> None:
        """Advance time by the specified number of milliseconds"""
        self.sender.tick(ms)
        if expect_max_retx_exceeded:
            assert self.sender.retrans_count > MAX_RETX_ATTEMPTS, \
                f"{self.test_name}: Expected max retransmissions exceeded but got {self.sender.retrans_count} retransmissions"
    
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

    # Test SYN
    def test_syn_sent_after_first_push(self):
        """Test that SYN is sent after first push"""
        test = TCPSenderTestHarness("SYN sent after first push")
        
        # Initial push should trigger SYN
        test.push()
        test.expect_message(no_flags=False, syn=True, payload_size=0, seqno=test.isn)
        test.expect_seqno(test.isn + 1)
        test.expect_seqnos_in_flight(1)
        
        self.assertFalse(test.has_error())

    def test_syn_acked(self):
        """Test SYN being acknowledged"""
        test = TCPSenderTestHarness("SYN acked test")
        
        # Send SYN
        test.push()
        test.expect_message(no_flags=False, syn=True, payload_size=0, seqno=test.isn)
        test.expect_seqno(test.isn + 1)
        test.expect_seqnos_in_flight(1)
        
        # Receive ACK for SYN
        test.receive_ack(test.isn + 1)
        test.expect_no_segment()
        test.expect_seqnos_in_flight(0)

    def test_syn_wrong_ack(self):
        """Test SYN receiving wrong acknowledgment"""
        test = TCPSenderTestHarness("SYN -> wrong ack test")
        
        # Send SYN
        test.push()
        test.expect_message(no_flags=False, syn=True, payload_size=0, seqno=test.isn)
        test.expect_seqno(test.isn + 1)
        test.expect_seqnos_in_flight(1)
        
        # Receive wrong ACK
        test.receive_ack(test.isn)
        test.expect_seqno(test.isn + 1)
        test.expect_no_segment()
        test.expect_seqnos_in_flight(1)

    def test_syn_acked_with_data(self):
        """Test sending data after SYN is acknowledged"""
        test = TCPSenderTestHarness("SYN acked, data")
        
        # Send SYN
        test.push()
        test.expect_message(no_flags=False, syn=True, payload_size=0, seqno=test.isn)
        test.expect_seqno(test.isn + 1)
        test.expect_seqnos_in_flight(1)
        
        # Receive ACK for SYN
        test.receive_ack(test.isn + 1)
        test.expect_no_segment()
        test.expect_seqnos_in_flight(0)
        
        # Send data
        test.push("abcdefgh")
        test.tick(1)
        test.expect_message(seqno=test.isn + 1, data="abcdefgh")
        test.expect_seqno(test.isn + 9)  # ISN + 1 (SYN) + 8 (data)
        test.expect_seqnos_in_flight(8)
        
        # Receive ACK for data
        test.receive_ack(test.isn + 9)
        test.expect_no_segment()
        test.expect_seqnos_in_flight(0)
        test.expect_seqno(test.isn + 9)

    # Test Retx
    def test_retx_syn_twice_then_ack(self):
        """Test retransmitting SYN twice at the right times, then acknowledge"""
        retx_timeout = random.randint(10, 10000)
        test = TCPSenderTestHarness("Retx SYN twice at the right times, then ack", retx_timeout=retx_timeout)
        
        # Initial SYN
        test.push()
        test.expect_message(no_flags=False, syn=True, payload_size=0, seqno=test.isn)
        test.expect_no_segment()
        test.expect_seqno(test.isn + 1)
        test.expect_seqnos_in_flight(1)
        
        # Wait just before timeout
        test.tick(retx_timeout - 1)
        test.expect_no_segment()
        
        # First retransmission
        test.tick(1)
        test.expect_message(no_flags=False, syn=True, payload_size=0, seqno=test.isn)
        test.expect_seqno(test.isn + 1)
        test.expect_seqnos_in_flight(1)
        
        # Wait just before second timeout (doubled)
        test.tick(2 * retx_timeout - 1)
        test.expect_no_segment()
        
        # Second retransmission
        test.tick(1)
        test.expect_message(no_flags=False, syn=True, payload_size=0, seqno=test.isn)
        test.expect_seqno(test.isn + 1)
        test.expect_seqnos_in_flight(1)
        
        # Finally receive ACK
        test.receive_ack(test.isn + 1)
        test.expect_seqno(test.isn + 1)
        test.expect_seqnos_in_flight(0)
        
        self.assertFalse(test.has_error())

    def test_retx_syn_until_too_many(self):
        """Test retransmitting SYN until max retransmissions exceeded"""
        retx_timeout = random.randint(10, 10000)
        test = TCPSenderTestHarness("Retx SYN until too many retransmissions", retx_timeout=retx_timeout)
        
        # Initial SYN
        test.push()
        test.expect_message(no_flags=False, syn=True, payload_size=0, seqno=test.isn)
        test.expect_no_segment()
        test.expect_seqno(test.isn + 1)
        test.expect_seqnos_in_flight(1)
        
        # Retransmit until max attempts
        for attempt in range(MAX_RETX_ATTEMPTS):
            # Wait just before timeout
            test.tick((retx_timeout << attempt) - 1, expect_max_retx_exceeded=False)
            test.expect_no_segment()
            
            # Timeout and retransmit
            test.tick(1, expect_max_retx_exceeded=False)
            test.expect_message(no_flags=False, syn=True, payload_size=0, seqno=test.isn)
            test.expect_seqno(test.isn + 1)
            test.expect_seqnos_in_flight(1)
        
        # Final timeout should exceed max retransmissions
        test.tick((retx_timeout << MAX_RETX_ATTEMPTS) - 1, expect_max_retx_exceeded=False)
        test.tick(1, expect_max_retx_exceeded=True)

    def test_retx_with_data(self):
        """Test retransmission with data segments"""
        retx_timeout = random.randint(10, 10000)
        test = TCPSenderTestHarness("Send some data, then retx and succeed, then retx till limit", retx_timeout=retx_timeout)
        
        # Initial SYN and ACK
        test.push()
        test.expect_message(no_flags=False, syn=True, payload_size=0, seqno=test.isn)
        test.expect_no_segment()
        test.receive_ack(test.isn + 1)
        
        # Send first data segment
        test.push("abcd")
        test.expect_message(payload_size=4)
        test.expect_no_segment()
        test.receive_ack(test.isn + 5)
        test.expect_seqnos_in_flight(0)
        
        # Send second data segment
        test.push("efgh")
        test.expect_message(payload_size=4)
        test.expect_no_segment()
        
        # Retransmit after timeout
        test.tick(retx_timeout)
        test.expect_message(payload_size=4)
        test.expect_no_segment()
        
        # Receive ACK and send new data
        test.receive_ack(test.isn + 9)
        test.expect_seqnos_in_flight(0)
        test.push("ijkl")
        test.expect_message(payload_size=4, seqno=test.isn + 9)
        
        # Retransmit until max attempts
        for attempt in range(MAX_RETX_ATTEMPTS):
            test.tick((retx_timeout << attempt) - 1, expect_max_retx_exceeded=False)
            test.expect_no_segment()
            test.tick(1, expect_max_retx_exceeded=False)
            test.expect_message(payload_size=4, seqno=test.isn + 9)
            test.expect_seqnos_in_flight(4)
        
        # Final timeout should exceed max retransmissions
        test.tick((retx_timeout << MAX_RETX_ATTEMPTS) - 1, expect_max_retx_exceeded=False)
        test.tick(1, expect_max_retx_exceeded=True)

    def test_retx_earliest_packet(self):
        """Test retransmission of earliest unacknowledged packet"""
        retx_timeout = random.randint(10, 10000)
        test = TCPSenderTestHarness("Retx after multiple sends, retx earliest packet", retx_timeout=retx_timeout)
        
        # Initial SYN and ACK
        test.push()
        test.expect_message(no_flags=False, syn=True, payload_size=0, seqno=test.isn)
        test.expect_no_segment()
        test.expect_seqnos_in_flight(1)
        test.receive_ack(test.isn + 1)
        test.expect_seqnos_in_flight(0)
        
        # Send segment A
        test.push("A")
        test.expect_message(payload_size=1, seqno=test.isn + 1)
        test.expect_no_segment()
        test.expect_seqnos_in_flight(1)
        
        # Queue segment B
        test.push("BB")
        test.expect_seqnos_in_flight(3)
        
        # Timeout to retransmit A and B
        test.tick(retx_timeout)
        test.expect_message()  # Either A or B
        test.expect_message()  # Either A or B
        test.expect_no_segment()
        test.expect_seqnos_in_flight(3)
        test.expect_consecutive_retransmissions(1)
        
        # Second timeout should retransmit A (earliest unacked)
        test.tick(retx_timeout << 1)
        test.expect_message(payload_size=1, seqno=test.isn + 1)
        test.expect_no_segment()
        test.expect_seqnos_in_flight(3)
        test.expect_consecutive_retransmissions(2)
        
        # Acknowledge A
        test.receive_ack(test.isn + 2)
        test.expect_seqnos_in_flight(2)
        test.expect_consecutive_retransmissions(0)
        
        # Timeout should retransmit B
        test.tick(retx_timeout)
        test.expect_message(payload_size=2, seqno=test.isn + 2)
        test.expect_no_segment()
        test.expect_consecutive_retransmissions(1)
        
        # Acknowledge B
        test.receive_ack(test.isn + 4)
        test.expect_seqnos_in_flight(0)
        test.expect_no_segment()

    def test_timer_correctness(self):
        """Test timer behavior and retransmission timing"""
        retx_timeout = random.randint(10, 10000)
        test = TCPSenderTestHarness("timer correctness", retx_timeout=retx_timeout)
        
        # Initial SYN and ACK
        test.push()
        test.expect_message(no_flags=False, syn=True, payload_size=0, seqno=test.isn)
        test.expect_no_segment()
        test.expect_seqnos_in_flight(1)
        test.receive_ack(test.isn + 1)
        test.expect_seqnos_in_flight(0)
        
        # Timer should not trigger when no data in flight
        test.tick(retx_timeout)
        test.expect_no_segment()
        test.expect_seqnos_in_flight(0)
        
        # Send data
        test.push("a")
        test.expect_message(data="a")
        
        # Short tick should not trigger retransmission
        test.tick(1)
        test.expect_no_segment()
        test.expect_seqnos_in_flight(1)
        
        # Timeout should trigger retransmission
        test.tick(retx_timeout - 1)
        test.expect_message(data="a")
        test.expect_seqnos_in_flight(1)
        
        # Acknowledge data
        test.receive_ack(test.isn + 2)
        test.expect_no_segment()
        test.expect_seqnos_in_flight(0)
        
        self.assertFalse(test.has_error())

    def test_three_short_writes(self):
        """Test three consecutive short writes"""
        test = TCPSenderTestHarness("Three short writes")
        
        # Initial SYN
        test.push()
        test.expect_message(no_flags=False, syn=True, payload_size=0, seqno=test.isn)
        test.expect_seqno(test.isn + 1)
        test.expect_seqnos_in_flight(1)
        
        # Receive ACK for SYN
        test.receive_ack(test.isn + 1)
        test.expect_seqno(test.isn + 1)
        test.expect_seqnos_in_flight(0)
        
        # First write
        test.push("ab")
        test.expect_message(data="ab", seqno=test.isn + 1)
        
        # Second write
        test.push("cd")
        test.expect_message(data="cd", seqno=test.isn + 3)
        
        # Third write
        test.push("abcd")
        test.expect_message(data="abcd", seqno=test.isn + 5)
        test.expect_seqno(test.isn + 9)
        test.expect_seqnos_in_flight(8)

    def test_many_short_writes_continuous_acks(self):
        """Test many short writes with continuous acknowledgments"""
        test = TCPSenderTestHarness("Many short writes, continuous acks")
        
        # Initial SYN
        test.push()
        test.expect_message(no_flags=False, syn=True, payload_size=0, seqno=test.isn)
        test.receive_ack(test.isn + 1)
        test.expect_seqno(test.isn + 1)
        test.expect_seqnos_in_flight(0)
        
        # Multiple rounds of writes and acks
        max_block_size = 10
        n_rounds = 10000
        bytes_sent = 0
        
        for i in range(n_rounds):
            # Generate random data
            block_size = random.randint(1, max_block_size)
            data = ''.join(chr(ord('a') + ((i + j) % 26)) for j in range(block_size))
            
            test.expect_seqno(test.isn + bytes_sent + 1)
            test.push(data)
            bytes_sent += block_size
            test.expect_seqnos_in_flight(block_size)
            test.expect_message(seqno=test.isn + 1 + (bytes_sent - block_size), data=data)
            test.expect_no_segment()
            test.receive_ack(test.isn + 1 + bytes_sent)

    def test_many_short_writes_ack_at_end(self):
        """Test many short writes with acknowledgment at the end"""
        test = TCPSenderTestHarness("Many short writes, ack at end")
        
        # Initial SYN
        test.push()
        test.expect_message(no_flags=False, syn=True, payload_size=0, seqno=test.isn)
        test.expect_seqno(test.isn + 1)
        test.expect_seqnos_in_flight(1)
        
        # Receive ACK for SYN with large window
        test.receive_ack(test.isn + 1, window_size=65000)
        test.expect_seqno(test.isn + 1)
        test.expect_seqnos_in_flight(0)
        
        # Multiple rounds of writes
        max_block_size = 10
        n_rounds = 1000
        bytes_sent = 0
        
        for i in range(n_rounds):
            # Generate random data
            block_size = random.randint(1, max_block_size)
            data = ''.join(chr(ord('a') + ((i + j) % 26)) for j in range(block_size))
            
            test.expect_seqno(test.isn + bytes_sent + 1)
            test.push(data)
            bytes_sent += block_size
            test.expect_seqnos_in_flight(bytes_sent)
            test.expect_message(seqno=test.isn + 1 + (bytes_sent - block_size), data=data)
            test.expect_no_segment()
        
        # Final acknowledgment
        test.expect_seqnos_in_flight(bytes_sent)
        test.receive_ack(test.isn + 1 + bytes_sent)
        test.expect_seqnos_in_flight(0)

    def test_window_filling(self):
        """Test filling and respecting the window size"""
        test = TCPSenderTestHarness("Window filling")
        
        # Initial SYN
        test.push()
        test.expect_message(no_flags=False, syn=True, payload_size=0, seqno=test.isn)
        test.expect_seqno(test.isn + 1)
        test.expect_seqnos_in_flight(1)
        
        # Receive ACK with window size 3
        test.receive_ack(test.isn + 1, window_size=3)
        test.expect_seqno(test.isn + 1)
        test.expect_seqnos_in_flight(0)
        
        # Try to send more than window size
        test.push("01234567")
        test.expect_seqnos_in_flight(3)
        test.expect_message(data="012")
        test.expect_no_segment()
        test.expect_seqno(test.isn + 4)
        
        # Acknowledge first segment, send next
        test.receive_ack(test.isn + 4, window_size=3)
        test.push()
        test.expect_seqnos_in_flight(3)
        test.expect_message(data="345")
        test.expect_no_segment()
        test.expect_seqno(test.isn + 7)
        
        # Acknowledge second segment, send final part
        test.receive_ack(test.isn + 7, window_size=3)
        test.push()
        test.expect_seqnos_in_flight(2)
        test.expect_message(data="67")
        test.expect_no_segment()
        test.expect_seqno(test.isn + 9)
        
        # Final acknowledgment
        test.receive_ack(test.isn + 9, window_size=3)
        test.expect_seqnos_in_flight(0)
        test.expect_no_segment()

    def test_immediate_writes_respect_window(self):
        """Test that immediate writes respect the window size"""
        test = TCPSenderTestHarness("Immediate writes respect the window")
        
        # Initial SYN
        test.push()
        test.expect_message(no_flags=False, syn=True, payload_size=0, seqno=test.isn)
        test.expect_seqno(test.isn + 1)
        test.expect_seqnos_in_flight(1)
        
        # Receive ACK with window size 3
        test.receive_ack(test.isn + 1, window_size=3)
        test.expect_seqno(test.isn + 1)
        test.expect_seqnos_in_flight(0)
        
        # First write fits in window
        test.push("01")
        test.expect_seqnos_in_flight(2)
        test.expect_message(data="01")
        test.expect_no_segment()
        test.expect_seqno(test.isn + 3)
        
        # Second write partially fits in window
        test.push("23")
        test.expect_seqnos_in_flight(3)
        test.expect_message(data="2")
        test.expect_no_segment()
        test.expect_seqno(test.isn + 4)

if __name__ == '__main__':
    unittest.main()