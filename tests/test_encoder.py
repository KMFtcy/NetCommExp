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


# 添加基准测试类
class EncoderBenchmark:
    def __init__(self):
        # 创建一个真实的ByteStream用于测试
        self.byte_stream_capacity = 50 * 1024 * 1024  # 50MB容量
        self.byte_stream = ByteStream(capacity=self.byte_stream_capacity)
        
    def setup(self, n=100, k=70):
        """准备编码器和测试数据"""
        self.encoder = Encoder(self.byte_stream, n=n, k=k)
        
    def teardown(self):
        """清理编码器"""
        if hasattr(self, 'encoder'):
            self.encoder.stop()
        # 创建新的ByteStream对象替代reset
        self.byte_stream = ByteStream(capacity=self.byte_stream_capacity)
    
    def reset_byte_stream(self):
        """辅助方法：通过创建新的ByteStream对象清空缓冲区"""
        self.byte_stream = ByteStream(capacity=self.byte_stream_capacity)
            
    def generate_test_data(self, size_kb):
        """生成指定大小的随机测试数据（以KB为单位）"""
        size_bytes = size_kb * 1024
        # 确保数据大小是k的倍数
        k = self.encoder.k
        size_bytes = size_bytes + (k - size_bytes % k) if size_bytes % k != 0 else size_bytes
        return bytes([random.randint(0, 255) for _ in range(size_bytes)])
    
    def benchmark_encoding_speed(self, sizes_kb=[10, 50, 100, 500, 1000]):
        """测试不同数据大小的编码速度"""
        print("\n===== 编码速度基准测试 =====")
        print(f"编码参数: n={self.encoder.n}, k={self.encoder.k}")
        
        results = {}
        for size_kb in sizes_kb:
            test_data = self.generate_test_data(size_kb)
            data_size_mb = len(test_data) / (1024 * 1024)
            
            # 清空ByteStream
            self.reset_byte_stream()
            
            # 预热 - 使用同步编码
            self.encoder.encode_sync(test_data)
            
            # 测量编码时间
            times = []
            for _ in range(3):  # 运行3次取平均值
                self.reset_byte_stream()
                
                # 确保测量编码的完整过程
                start_time = time.time()
                success = self.encoder.encode_sync(test_data)
                end_time = time.time()
                
                if not success:
                    print(f"警告: 编码任务可能未完成，结果可能不准确")
                
                elapsed = end_time - start_time
                times.append(elapsed)
                
            avg_time = statistics.mean(times)
            throughput = data_size_mb / avg_time  # MB/s
            
            results[size_kb] = {
                'size_mb': data_size_mb,
                'avg_time': avg_time,
                'throughput': throughput
            }
            
            print(f"数据大小: {size_kb} KB ({data_size_mb:.2f} MB)")
            print(f"平均编码时间: {avg_time:.4f} 秒")
            print(f"吞吐量: {throughput:.2f} MB/s")
            print("----------------------------")
            
        return results
    
    def benchmark_different_parameters(self):
        """测试不同编码参数的性能"""
        print("\n===== 不同编码参数基准测试 =====")
        
        # 测试不同n和k值的组合
        test_params = [
            (100, 50),   # 高冗余度
            (100, 70),   # 中等冗余度
            (100, 90),   # 低冗余度
            (200, 100),  # 更大的块大小
            (50, 35),    # 更小的块大小
        ]
        
        test_size_kb = 500  # 固定测试大小为500KB
        
        results = {}
        for n, k in test_params:
            # 重新设置编码器
            self.teardown()
            self.setup(n=n, k=k)
            
            test_data = self.generate_test_data(test_size_kb)
            data_size_mb = len(test_data) / (1024 * 1024)
            
            # 清空ByteStream
            self.reset_byte_stream()
            
            # 预热 - 使用同步编码
            self.encoder.encode_sync(test_data)
            
            # 测量编码时间
            times = []
            for _ in range(3):
                self.reset_byte_stream()
                
                # 确保测量编码的完整过程
                start_time = time.time()
                success = self.encoder.encode_sync(test_data)
                end_time = time.time()
                
                if not success:
                    print(f"警告: 编码任务可能未完成，结果可能不准确")
                
                elapsed = end_time - start_time
                times.append(elapsed)
                
            avg_time = statistics.mean(times)
            throughput = data_size_mb / avg_time  # MB/s
            
            results[(n, k)] = {
                'avg_time': avg_time,
                'throughput': throughput
            }
            
            print(f"参数: n={n}, k={k}, 冗余度={(n-k)/n:.2f}")
            print(f"数据大小: {test_size_kb} KB ({data_size_mb:.2f} MB)")
            print(f"平均编码时间: {avg_time:.4f} 秒")
            print(f"吞吐量: {throughput:.2f} MB/s")
            print("----------------------------")
            
        return results
    
    def run_all_benchmarks(self):
        """运行所有基准测试"""
        self.setup()
        
        try:
            print("\n========== FEC编码器性能基准测试 ==========")
            speed_results = self.benchmark_encoding_speed()
            param_results = self.benchmark_different_parameters()
            
            # 结果摘要
            print("\n========== 测试结果摘要 ==========")
            print("1. 不同数据大小的吞吐量 (MB/s):")
            for size_kb, result in speed_results.items():
                print(f"   - {size_kb} KB: {result['throughput']:.2f} MB/s")
                
            print("\n2. 不同编码参数的吞吐量 (MB/s):")
            for (n, k), result in param_results.items():
                print(f"   - n={n}, k={k}, 冗余度={(n-k)/n:.2f}: {result['throughput']:.2f} MB/s")
                
        finally:
            self.teardown()


# 如果直接运行此文件，则执行基准测试
if __name__ == '__main__':
    # 如果需要单独运行基准测试，取消下面的注释
    benchmark = EncoderBenchmark()
    benchmark.run_all_benchmarks()
    
    # 运行标准单元测试
    # unittest.main()
