import ReedSolomon2 as RS
import random
import time

def encoding_rate(n, k, method="standard", num_tests=5, msg_size=1000):
    """
    Measure the Reed-Solomon encoding rate using parameters n and k.
    
    Parameters:
        n: Length of the encoded message
        k: Length of the original message (number of information symbols)
        method: "standard" or "systematic"
        num_tests: Number of test runs
        msg_size: The number of 8 bit numbers in a message
        
    Returns:
        Encoding rate (Mbps)
    """
    # Create Reed-Solomon encoder
    rs = RS.ReedSolomon(n, k)
    
    # Generate test messages
    messages = []
    for _ in range(num_tests):
        # Create a message with k rows, each row having msg_size elements
        message = [[random.randint(0, 255) for _ in range(msg_size)] for _ in range(k)]
        messages.append(message)
        # print the number of bytes in the message
        print(f"Number of bytes in the message: {len(message) * msg_size}")

    # Choose encoding function based on method
    if method == "systematic":
        encode_func = rs.encode_systematic
    else:
        encode_func = rs.encode
    
    # Measure encoding time
    total_time = 0
    for message in messages:
        start_time = time.time()
        encode_func(message)
        end_time = time.time()
        total_time += (end_time - start_time)
    
    # Calculate total data size processed
    total_symbols = num_tests * k * msg_size
    
    # Calculate rate (Mbps) - 8 bits per symbol, convert to Mbps
    rate = ((total_symbols / total_time) * 8) / 1000000 if total_time > 0 else 0
    
    return rate

def decoding_rate(n, k, method="standard", num_tests=10, msg_size=1000):
    """
    Measure the Reed-Solomon decoding rate using parameters n and k.
    
    Parameters:
        n: Length of the encoded message
        k: Length of the original message (number of information symbols)
        method: "standard" or "systematic"
        num_tests: Number of test runs
        msg_size: The number of 8 bit numbers in a message
        
    Returns:
        Decoding rate (Mbps)
    """
    # Create Reed-Solomon encoder/decoder
    rs = RS.ReedSolomon(n, k)
    
    # Generate test messages and encode them
    encoded_messages = []
    for _ in range(num_tests):
        # Create a message with k rows, each row having msg_size elements
        message = [[random.randint(0, 255) for _ in range(msg_size)] for _ in range(k)]
        
        # Encode based on method
        if method == "systematic":
            encoded_message = rs.encode_systematic(message)
        else:
            encoded_message = rs.encode(message)
            
        encoded_messages.append(encoded_message)
    
    # For each encoded message, select k indices for decoding
    indices_list = []
    for _ in range(num_tests):
        indices = random.sample(range(n), k)
        indices_list.append(indices)
    
    # Measure decoding time
    total_time = 0
    for i in range(num_tests):
        encoded_msg = encoded_messages[i]
        indices = indices_list[i]
        
        # Extract symbols at selected indices
        received = [encoded_msg[idx] for idx in indices]
        
        start_time = time.time()
        if method == "systematic":
            rs.decode_systematic(received, indices)
        else:
            rs.decode(received, indices)
        end_time = time.time()
        
        total_time += (end_time - start_time)
    
    # Calculate total data size processed
    total_symbols = num_tests * k * msg_size
    
    # Calculate rate (Mbps) - 8 bits per symbol, convert to Mbps
    rate = ((total_symbols / total_time) * 8) / 1000000 if total_time > 0 else 0
    
    return rate

def run_benchmarks():
    """Run a series of benchmarks and print the results."""
    # Test parameters
    n_values = [7, 15, 31]
    k_values = [3, 7, 15]
    methods = ["standard", "systematic"]
    msg_sizes = [100, 1000, 10000]
    
    print("Reed-Solomon Code Performance Benchmarks")
    print("=======================================")
    
    for n in n_values:
        for k in k_values:
            if k < n:
                print(f"\nParameters: n={n}, k={k}")
                print("-" * 40)
                
                for method in methods:
                    print(f"\nMethod: {method}")
                    print("Message Size  | Encoding Rate (Mbps) | Decoding Rate (Mbps)")
                    print("-------------|-------------------|------------------")
                    
                    for size in msg_sizes:
                        enc_rate = encoding_rate(n, k, method, num_tests=10, msg_size=size)
                        dec_rate = decoding_rate(n, k, method, num_tests=10, msg_size=size)
                        print(f"{size:11d} | {enc_rate:17.4f} | {dec_rate:17.4f}")

def various_n():
    """Test the effect of different n values on encoding and decoding rates"""
    k = 100
    n_values = list(range(100, 257, 10))  # from 100 to 256, step 10
    methods = ["standard", "systematic"]
    msg_size = 1000
    
    print("\nTest with fixed k=100, varying n values")
    print("==============================")
    
    for method in methods:
        print(f"\nMethod: {method}")
        print("n value | Encoding Rate (Mbps) | Decoding Rate (Mbps)")
        print("---------|-------------------|------------------")
        
        for n in n_values:
            enc_rate = encoding_rate(n, k, method, num_tests=5, msg_size=msg_size)
            dec_rate = decoding_rate(n, k, method, num_tests=5, msg_size=msg_size)
            print(f"{n:7d} | {enc_rate:17.4f} | {dec_rate:17.4f}")

def various_k():
    """Test the effect of different k values on encoding and decoding rates"""
    n = 150
    k_values = list(range(10, 151, 10))  # from 10 to 150, step 10
    methods = ["standard", "systematic"]
    msg_size = 1000
    
    print("\nTest with fixed n=150, varying k values")
    print("==============================")
    
    for method in methods:
        print(f"\nMethod: {method}")
        print("k value | Encoding Rate (Mbps) | Decoding Rate (Mbps)")
        print("---------|-------------------|------------------")
        
        for k in k_values:
            enc_rate = encoding_rate(n, k, method, num_tests=5, msg_size=msg_size)
            dec_rate = decoding_rate(n, k, method, num_tests=5, msg_size=msg_size)
            print(f"{k:7d} | {enc_rate:17.4f} | {dec_rate:17.4f}")

def various_msg_size():
    """Test the effect of different message sizes on encoding and decoding rates"""
    n = 150
    k = 100
    # Create 50 test points
    small_sizes = list(range(10, 100, 10))  # 9 points: 10, 20, ..., 90
    medium_sizes = list(range(100, 1000, 40))  # 23 points: 100, 140, ..., 980
    large_sizes = list(range(1000, 5001, 200))  # 21 points: 1000, 1200, ..., 5000
    
    # Combine all test points
    msg_sizes = small_sizes + medium_sizes + large_sizes
    
    # Ensure only 50 test points
    msg_sizes = msg_sizes[:50]
    
    methods = ["standard", "systematic"]
    
    print(f"\nTest with fixed n=150, k=100, varying message sizes ({len(msg_sizes)} test points)")
    print("==============================")
    
    for method in methods:
        print(f"\nMethod: {method}")
        print("Msg Size | Encoding Rate (Mbps) | Decoding Rate (Mbps)")
        print("---------|-------------------|------------------")
        
        for size in msg_sizes:
            enc_rate = encoding_rate(n, k, method, num_tests=3, msg_size=size)
            dec_rate = decoding_rate(n, k, method, num_tests=3, msg_size=size)
            print(f"{size:8d} | {enc_rate:17.4f} | {dec_rate:17.4f}")


if __name__ == "__main__":
    # run_benchmarks()
    print("Reed-Solomon Encoding/Decoding Performance Test")
    print("=============================================")
    various_k()  # Test 1: n=150, k from 10 to 150
    various_n()  # Test 2: k=100, n from 100 to 256
    various_msg_size()  # Test 3: k=100, n=150, different msg_sizes
