import random
import time
from src.FEC.LTCoding import LTEncoder, LTDecoder

def encoding_rate(k, num_packets, dist_type="Robust Soliton", num_tests=100, msg_size=1000):
    """
    Measure the encoding rate of LT codes
    
    Parameters:
        k: Length of the original message (number of information symbols)
        num_packets: Number of packets to generate during encoding
        dist_type: Distribution type ("Robust Soliton", "Soliton", "Raptor")
        num_tests: Number of test runs
        msg_size: Size of each packet in the message
        
    Returns:
        Encoding rate (Mbps)
    """
    # Generate test messages
    messages = []
    for _ in range(num_tests):
        # Create a message with k packets, each with msg_size elements
        message = [[random.randint(0, 255) for _ in range(msg_size)] for _ in range(k)]
        messages.append(message)
    
    # Measure encoding time
    total_time = 0
    for message in messages:
        # Create LT encoder
        lt = LTEncoder(k)
        lt.set_degree_distribution(dist_type)
        lt.set_message_packets(message)
        
        start_time = time.time()
        lt.encode(range(num_packets))
        end_time = time.time()
        total_time += (end_time - start_time)
    
    # Calculate total data size processed
    total_symbols = num_tests * k * msg_size
    
    # Calculate rate (Mbps) - each symbol is 8 bits, converted to Mbps
    rate = ((total_symbols / total_time) * 8) / 1000000 if total_time > 0 else 0
    
    return rate

def decoding_rate(k, overhead_ratio=1.5, dist_type="Robust Soliton", num_tests=100, msg_size=1000):
    """
    Measure the decoding rate of LT codes
    
    Parameters:
        k: Length of the original message (number of information symbols)
        overhead_ratio: Ratio factor to determine the number of encoded packets received (typically extra overhead needed)
        dist_type: Distribution type ("Robust Soliton", "Soliton", "Raptor")
        num_tests: Number of test runs
        msg_size: Size of each packet in the message
        
    Returns:
        Decoding rate (Mbps)
    """
    # Calculate the number of packets to encode (based on overhead ratio)
    n = int(k * overhead_ratio)
    
    # Generate test messages and encode them
    encoded_messages = []
    for _ in range(num_tests):
        # Create a message with k packets, each with msg_size elements
        message = [[random.randint(0, 255) for _ in range(msg_size)] for _ in range(k)]
        
        # Create LT encoder and encode the message
        lt = LTEncoder(k)
        lt.set_degree_distribution(dist_type)
        lt.set_message_packets(message)
        
        # Encode the message
        encoded_message = lt.encode(range(n))
        encoded_messages.append((lt, encoded_message))
    
    # Measure decoding time
    total_time = 0
    for i in range(num_tests):
        lt, encoded_msg = encoded_messages[i]
        
        # Create a new LT decoder
        decoder = LTDecoder(k)
        decoder.set_degree_distribution(dist_type)
        
        start_time = time.time()
        decoder.set_received_packets(encoded_msg)
        decoder.check_decoding_status()
        decoder.get_decoded_message()
        end_time = time.time()
        
        total_time += (end_time - start_time)
    
    # Calculate total data size processed
    total_symbols = num_tests * k * msg_size
    
    # Calculate rate (Mbps) - each symbol is 8 bits, converted to Mbps
    rate = ((total_symbols / total_time) * 8) / 1000000 if total_time > 0 else 0
    
    return rate

def various_k():
    """Test the effect of different k values on encoding and decoding rates"""
    k_values = list(range(10, 151, 10))  # from 10 to 150, step 10
    dist_types = ["Robust Soliton", "Soliton", "Raptor"]
    msg_size = 1000
    overhead = 1.5
    
    print("\nTesting the effect of different k values (fixed msg_size=1000, overhead=1.5)")
    print("===================================================")
    
    for dist_type in dist_types:
        print(f"\nDistribution type: {dist_type}")
        print("k value | Encoding rate (Mbps) | Decoding rate (Mbps)")
        print("--------|---------------------|--------------------")
        
        for k in k_values:
            num_packets = int(k * overhead)
            enc_rate = encoding_rate(k, num_packets, dist_type, num_tests=5, msg_size=msg_size)
            dec_rate = decoding_rate(k, overhead, dist_type, num_tests=5, msg_size=msg_size)
            print(f"{k:5d} | {enc_rate:12.4f} | {dec_rate:13.4f}")

def various_overhead():
    """Test the effect of different overhead ratios on decoding rate"""
    k = 100
    overhead_values = [1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0]
    dist_types = ["Robust Soliton", "Soliton", "Raptor"]
    msg_size = 1000
    
    print("\nTesting the effect of different overhead ratios (fixed k=100, msg_size=1000)")
    print("===================================================")
    
    for dist_type in dist_types:
        print(f"\nDistribution type: {dist_type}")
        print("Overhead ratio | Decoding rate (Mbps)")
        print("--------------|--------------------")
        
        for overhead in overhead_values:
            num_packets = int(k * overhead)
            dec_rate = decoding_rate(k, overhead, dist_type, num_tests=5, msg_size=msg_size)
            print(f"{overhead:7.1f} | {dec_rate:13.4f}")

def various_msg_size():
    """Test the effect of different message sizes on encoding and decoding rates"""
    k = 100
    overhead = 1.5
    # Create test points
    small_sizes = list(range(10, 100, 10))  # 9 points: 10, 20, ..., 90
    medium_sizes = list(range(100, 1000, 40))  # 23 points: 100, 140, ..., 980
    large_sizes = list(range(1000, 5001, 200))  # 21 points: 1000, 1200, ..., 5000
    
    # Combine all test points
    msg_sizes = small_sizes + medium_sizes + large_sizes
    
    # Ensure not more than 50 test points
    msg_sizes = msg_sizes[:50]
    
    dist_types = ["Robust Soliton", "Soliton", "Raptor"]
    
    print(f"\nTesting the effect of different message sizes (fixed k=100, overhead=1.5, total {len(msg_sizes)} test points)")
    print("===================================================")
    
    for dist_type in dist_types:
        print(f"\nDistribution type: {dist_type}")
        print("Message size | Encoding rate (Mbps) | Decoding rate (Mbps)")
        print("------------|---------------------|--------------------")
        
        for size in msg_sizes:
            num_packets = int(k * overhead)
            enc_rate = encoding_rate(k, num_packets, dist_type, num_tests=3, msg_size=size)
            dec_rate = decoding_rate(k, overhead, dist_type, num_tests=3, msg_size=size)
            print(f"{size:7d} | {enc_rate:12.4f} | {dec_rate:13.4f}")

if __name__ == "__main__":
    print("LT Encoding/Decoding Performance Test")
    print("====================")
    various_k()  # Test 1: k from 10 to 150
    various_overhead()  # Test 2: overhead ratio from 1.1 to 2.0
    various_msg_size()  # Test 3: different message sizes