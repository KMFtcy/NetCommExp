import unittest
from src.retrans.cmltv_ACK import CAP, SegmentType, CAPSegment, make_packet, parse_packet

class TestCAPPacket(unittest.TestCase):
    def setUp(self):
        self.cap = CAP()
        self.test_payload = b'Hello, World!'
        self.test_seq_num = 1234
        self.test_ack_num = 5678

    def test_syn_packet(self):
        # Test SYN packet
        packet = make_packet(
            seg_type=SegmentType.SYN,
            seq_num=self.test_seq_num
        )
        parsed = parse_packet(packet)
        
        self.assertEqual(parsed.type, SegmentType.SYN)
        self.assertEqual(parsed.seq_num, self.test_seq_num)
        self.assertEqual(parsed.ack_num, 0)
        self.assertEqual(parsed.payload, b'')

    def test_syn_ack_packet(self):
        # Test SYN-ACK packet
        packet = make_packet(
            seg_type=SegmentType.SYN_ACK,
            seq_num=self.test_seq_num,
            ack_num=self.test_ack_num
        )
        parsed = parse_packet(packet)
        
        self.assertEqual(parsed.type, SegmentType.SYN_ACK)
        self.assertEqual(parsed.seq_num, self.test_seq_num)
        self.assertEqual(parsed.ack_num, self.test_ack_num)
        self.assertEqual(parsed.payload, b'')

    def test_data_packet(self):
        # Test DATA packet with payload
        packet = make_packet(
            seg_type=SegmentType.DATA,
            seq_num=self.test_seq_num,
            payload=self.test_payload
        )
        parsed = parse_packet(packet)
        
        self.assertEqual(parsed.type, SegmentType.DATA)
        self.assertEqual(parsed.seq_num, self.test_seq_num)
        self.assertEqual(parsed.ack_num, 0)
        self.assertEqual(parsed.payload, self.test_payload)

    def test_data_ack_packet(self):
        # Test DATA-ACK packet with payload
        packet = make_packet(
            seg_type=SegmentType.DATA_ACK,
            seq_num=self.test_seq_num,
            ack_num=self.test_ack_num,
            payload=self.test_payload
        )
        parsed = parse_packet(packet)
        
        self.assertEqual(parsed.type, SegmentType.DATA_ACK)
        self.assertEqual(parsed.seq_num, self.test_seq_num)
        self.assertEqual(parsed.ack_num, self.test_ack_num)
        self.assertEqual(parsed.payload, self.test_payload)

    def test_fin_packet(self):
        # Test FIN packet
        packet = make_packet(
            seg_type=SegmentType.FIN,
            seq_num=self.test_seq_num
        )
        parsed = parse_packet(packet)
        
        self.assertEqual(parsed.type, SegmentType.FIN)
        self.assertEqual(parsed.seq_num, self.test_seq_num)
        self.assertEqual(parsed.ack_num, 0)
        self.assertEqual(parsed.payload, b'')

    def test_fin_ack_packet(self):
        # Test FIN-ACK packet
        packet = make_packet(
            seg_type=SegmentType.FIN_ACK,
            seq_num=self.test_seq_num,
            ack_num=self.test_ack_num
        )
        parsed = parse_packet(packet)
        
        self.assertEqual(parsed.type, SegmentType.FIN_ACK)
        self.assertEqual(parsed.seq_num, self.test_seq_num)
        self.assertEqual(parsed.ack_num, self.test_ack_num)
        self.assertEqual(parsed.payload, b'')

    def test_reserved_field(self):
        # Test that reserved field is always 0
        for seg_type in SegmentType:
            packet = make_packet(
                seg_type=seg_type,
                seq_num=self.test_seq_num,
                ack_num=self.test_ack_num
            )
            parsed = parse_packet(packet)
            self.assertEqual(parsed.reserved, 0)

    def tearDown(self):
        self.cap.socket.close()

if __name__ == '__main__':
    unittest.main() 