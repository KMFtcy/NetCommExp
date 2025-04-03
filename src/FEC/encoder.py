import threading
from enum import Enum
import time
import LTCoding as LTC
import ReedSolomon2 as RS
from src.util.ringbuffer import RingBuffer
from src.util.byte_stream import ByteStream


class CodeType(Enum):
    REED_SOLOMON = 1
    LT_CODING = 2


class Encoder:
    def __init__(self, byte_stream: ByteStream, code_type=CodeType.REED_SOLOMON, buffer_size=1024*1024, n=100, k=70):
        """
        Initialize the encoder
        
        Parameters:
            byte_stream: The target stream to write encoded data
            code_type: The encoding method, default is Reed-Solomon
            buffer_size: The size of the internal buffer
            n: The encoding parameter n (total symbols)
            k: The encoding parameter k (original symbols)
        """
        self.byte_stream = byte_stream
        self.code_type = code_type
        self.buffer = RingBuffer(buffer_size)
        self.n = n
        self.k = k
        self.thread = None
        self.running = False
        
        # 初始化编码器
        if self.code_type == CodeType.REED_SOLOMON:
            self.codec = RS.ReedSolomon(n, k)
        else:
            self.codec = LTC.LTEncoder(k)
            
    def encode(self, data : list[list[int]]):
        """
        Encode the input data and store it in the internal buffer
        
        Parameters:
            data: The data to be encoded
        """
        # 将输入数据分成k个符号
        packets = self._prepare_data(data)
        
        # 根据不同编码方式进行编码
        if self.code_type == CodeType.REED_SOLOMON:
            # 使用RS的系统化模式编码
            encoded_data = self.codec.encode_systematic(packets)
        elif self.code_type == CodeType.LT_CODING:
            # 使用LT编码
            self.codec.set_message_packets(packets)
            encoded_data = self.codec.encode(range(self.n))
            encoded_data = [packet[1] for packet in encoded_data]  # 提取数据部分
        
        # 将编码后的数据序列化并存入缓冲区
        serialized_data = self._serialize_encoded_data(encoded_data)
        self._store_to_buffer(serialized_data)
        
        # 如果线程未运行，启动线程
        if not self.running:
            self.start_transmission()
    
    def _prepare_data(self, data : list[list[int]]):
        """将输入数据分割为k个符号"""
        if isinstance(data, bytes):
            # 计算每个符号大小
            symbol_size = len(data) // self.k
            if symbol_size == 0:
                symbol_size = 1
            
            packets = []
            for i in range(self.k):
                start = i * symbol_size
                end = start + symbol_size if i < self.k - 1 else len(data)
                packets.append(list(data[start:end]))
            return packets
        else:
            # 如果已经是列表格式
            return data
    
    def _serialize_encoded_data(self, encoded_data):
        """将编码后的数据序列化为字节流"""
        result = bytearray()
        for packet in encoded_data:
            # 将每个符号序列化为字节
            if isinstance(packet, list):
                packet_bytes = bytes(packet)
            else:
                packet_bytes = packet
            
            # 添加符号长度头部
            length = len(packet_bytes)
            result.extend(length.to_bytes(4, byteorder='big'))
            result.extend(packet_bytes)
        
        return bytes(result)
    
    def _store_to_buffer(self, data):
        """将数据存储到内部缓冲区"""
        if len(data) > self.buffer.get_available_space():
            raise ValueError("编码后的数据超出缓冲区容量")
        self.buffer.push(data)
    
    def start_transmission(self):
        """启动传输线程"""
        if self.thread is None or not self.thread.is_alive():
            self.running = True
            self.thread = threading.Thread(target=self._transmission_loop)
            self.thread.daemon = True
            self.thread.start()
    
    def stop_transmission(self):
        """停止传输线程"""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
    
    def _transmission_loop(self):
        """传输循环，将缓冲区数据写入ByteStream"""
        while self.running:
            # 检查缓冲区是否有数据
            if not self.buffer.is_empty():
                # 检查ByteStream是否有足够空间
                available_space = self.byte_stream.available_capacity()
                if available_space > 0:
                    # 确定要传输多少数据
                    data_size = min(available_space, self.buffer.get_size())
                    # 从缓冲区中获取数据
                    data = self.buffer.pop(data_size)
                    # 写入到ByteStream
                    try:
                        self.byte_stream.push(data)
                    except ValueError as e:
                        # 处理流已关闭或容量不足的情况
                        print(f"传输错误: {e}")
                        time.sleep(0.01)  # 避免CPU过度使用
                else:
                    # ByteStream没有足够空间，等待
                    time.sleep(0.01)
            else:
                # 缓冲区为空，等待
                time.sleep(0.01)



