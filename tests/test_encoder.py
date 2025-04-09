import unittest
import threading
import queue
import time
import os
import sys
import random
from unittest.mock import MagicMock, patch

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.FEC.encoder import Encoder, CodeType
from src.util.byte_stream import ByteStream


class TestEncoder(unittest.TestCase):
    def setUp(self):
        # 创建一个模拟的ByteStream用于测试
        self.mock_byte_stream = MagicMock(spec=ByteStream)
        self.mock_byte_stream.available_capacity.return_value = 1000
        
    def tearDown(self):
        # 确保每个测试后encoder都被停止
        if hasattr(self, 'encoder') and self.encoder:
            self.encoder.stop()

    def test_init_reed_solomon(self):
        """测试使用Reed-Solomon编码初始化encoder"""
        encoder = Encoder(self.mock_byte_stream, code_type=CodeType.REED_SOLOMON, n=100, k=70)
        self.assertEqual(encoder.code_type, CodeType.REED_SOLOMON)
        self.assertEqual(encoder.n, 100)
        self.assertEqual(encoder.k, 70)
        self.assertTrue(encoder.running)
        encoder.stop()
        

    def test_init_lt_coding(self):
        """测试使用LT编码初始化encoder"""
        # 验证LT编码初始化时会抛出ValueError（未实现的功能）
        with self.assertRaises(ValueError) as context:
            encoder = Encoder(self.mock_byte_stream, code_type=CodeType.LT_CODING, n=100, k=70)
        
        # 验证异常消息内容是否正确
        self.assertIn("LT Coding is not supported yet", str(context.exception))
        
        # 不需要调用encoder.stop()，因为encoder对象未成功创建

    def test_encode_bytes_data(self):
        """测试编码bytes类型数据"""
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
        
        # 给编码线程一些时间来处理数据
        time.sleep(0.5)
        
        # 验证ByteStream.push被调用
        self.mock_byte_stream.push.assert_called()
        encoder.stop()

    def test_encode_list_data(self):
        """测试编码list类型数据"""
        k = 5
        encoder = Encoder(self.mock_byte_stream, n=10, k=k)
        # Exactly k packets to match encoding parameter
        test_data = [b"packet1", b"packet2", b"packet3", b"packet4", b"packet5"]
        # Ensure all packets have the same length
        max_len = max(len(p) for p in test_data)
        padded_data = [p + b"\x00" * (max_len - len(p)) for p in test_data]
        
        encoder.encode(padded_data)
        
        # 给编码线程一些时间来处理数据
        time.sleep(0.5)
        
        # 验证ByteStream.push被调用
        self.mock_byte_stream.push.assert_called()
        encoder.stop()
    
    def test_insufficient_space(self):
        """测试ByteStream空间不足的情况"""
        # 模拟一个容量很小的ByteStream
        self.mock_byte_stream.available_capacity.return_value = 10
        encoder = Encoder(self.mock_byte_stream, n=10, k=5)
        
        # 创建一个大于允许大小的数据
        test_data = b"This data is too large for the ByteStream"
        
        # 测试是否会抛出ValueError
        with self.assertRaises(ValueError):
            encoder.encode(test_data)
            
        encoder.stop()

    def test_empty_data(self):
        """测试编码空数据"""
        encoder = Encoder(self.mock_byte_stream, n=10, k=5)
        encoder.encode(b"")
        
        # 给编码线程一些时间来处理数据
        time.sleep(0.5)
        
        # 验证编码过程不会崩溃
        encoder.stop()
        
    def test_small_data(self):
        """测试编码小数据（小于k）"""
        k = 5
        encoder = Encoder(self.mock_byte_stream, n=10, k=k)
        # Create data that's exactly a multiple of k
        test_data = b"small" + b"\x00" * (k - 5 % k)
        
        encoder.encode(test_data)
        
        # 给编码线程一些时间来处理数据
        time.sleep(0.5)
        
        # 验证ByteStream.push被调用
        self.mock_byte_stream.push.assert_called()
        encoder.stop()
        
    def test_large_data(self):
        """测试编码大数据"""
        k = 5
        encoder = Encoder(self.mock_byte_stream, n=10, k=k)
        # Create data size that's a multiple of k
        data_size = 1000 + (k - 1000 % k) if 1000 % k != 0 else 1000
        large_data = bytes([random.randint(0, 255) for _ in range(data_size)])
        
        encoder.encode(large_data)
        
        # 给编码线程一些时间来处理数据
        time.sleep(0.5)
        
        # 验证ByteStream.push被调用
        self.mock_byte_stream.push.assert_called()
        encoder.stop()
        
    def test_multiple_encode_calls(self):
        """测试多次调用encode方法"""
        k = 5
        encoder = Encoder(self.mock_byte_stream, n=10, k=k)
        
        # 多次调用encode, ensure each call's data is a multiple of k
        for i in range(5):
            base_data = f"Test data {i}".encode()
            remainder = len(base_data) % k
            padding = (k - remainder) if remainder > 0 else 0
            padded_data = base_data + b"\x00" * padding
            
            encoder.encode(padded_data)
            time.sleep(0.1)  # 给一些时间处理
            
        # 验证ByteStream.push被调用了5次
        self.assertEqual(self.mock_byte_stream.push.call_count, 5)
        encoder.stop()
        
    def test_stop_and_restart(self):
        """测试停止和重启encoder"""
        encoder = Encoder(self.mock_byte_stream, n=10, k=5)
        self.assertTrue(encoder.running)
        
        # 停止encoder
        encoder.stop()
        self.assertFalse(encoder.running)
        
        # 重启encoder
        encoder.start()
        self.assertTrue(encoder.running)
        encoder.stop()
        
    def test_bytestream_full_during_encoding(self):
        """测试在编码过程中ByteStream变满的情况"""
        # 首先模拟ByteStream有足够空间
        k = 5
        self.mock_byte_stream.available_capacity.return_value = 1000
        encoder = Encoder(self.mock_byte_stream, n=10, k=k)
        
        # 模拟push时ByteStream已满的情况
        def side_effect(data):
            raise ValueError("ByteStream is full")
            
        self.mock_byte_stream.push.side_effect = side_effect
        
        # 尝试编码数据, ensure data is a multiple of k
        base_data = b"Test data"
        remainder = len(base_data) % k
        padding = (k - remainder) if remainder > 0 else 0
        test_data = base_data + b"\x00" * padding
        
        encoder.encode(test_data)
        
        # 给编码线程一些时间来处理数据
        time.sleep(0.5)
        
        # 验证push被调用但出现了错误
        self.mock_byte_stream.push.assert_called()
        encoder.stop()
        
    def test_different_n_k_values(self):
        """测试不同的n和k值"""
        # 测试k接近n的情况
        k1 = 95
        encoder1 = Encoder(self.mock_byte_stream, n=100, k=k1)
        base_data1 = b"Test data for high k/n ratio"
        remainder1 = len(base_data1) % k1
        padding1 = (k1 - remainder1) if remainder1 > 0 else 0
        test_data1 = base_data1 + b"\x00" * padding1
        
        encoder1.encode(test_data1)
        time.sleep(0.5)
        encoder1.stop()
        
        # 测试k远小于n的情况
        k2 = 20
        encoder2 = Encoder(self.mock_byte_stream, n=100, k=k2)
        base_data2 = b"Test data for low k/n ratio"
        remainder2 = len(base_data2) % k2
        padding2 = (k2 - remainder2) if remainder2 > 0 else 0
        test_data2 = base_data2 + b"\x00" * padding2
        
        encoder2.encode(test_data2)
        time.sleep(0.5)
        encoder2.stop()
        
        # 验证两种情况都能正常工作
        self.assertEqual(self.mock_byte_stream.push.call_count, 2)


if __name__ == '__main__':
    unittest.main()
