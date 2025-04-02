import random, math
from BipartiteGraph import BipartiteGraph
from LinearSystem import LinearSol, Matrix

class LTCommon: 
    """
    Common functions for LT Code and Raptor Code
    """
    def __init__(self, k):
        self.k = k
        self.degree_distribution = self.set_degree_distribution()

    def _ideal_soliton_dist(self, k):
        # Implement the Ideal Soliton distribution
        p = [0] * (k + 1)
        p[1] = 1 / k
        for i in range(2, k + 1):
            p[i] = p[i-1] + 1 / (i * (i - 1))
        return p

    def _robust_soliton_dist(self, c=0.1, delta=0.5):
        # Implement the Robust Soliton distribution
        R = max(1, math.sqrt(self.k) * c * math.log(self.k / delta))
        tau = [0] * (self.k + 1)
        for i in range(1, math.ceil(self.k / R)):
            tau[i] = R / (i * self.k)
        tau[math.ceil(self.k / R)] = R * math.log(R / delta) / self.k
        beta = sum(tau)
        p = self._ideal_soliton_dist(self.k)
        for i in range(1, self.k + 1):
            p[i] = (p[i] + sum(tau[:i+1])) / (1 + beta)
        return p

    def set_degree_distribution(self, dist_type="Robust Soliton"):
        if dist_type == "Soliton":
            self.degree_distribution = self._ideal_soliton_dist(self.k)
        elif dist_type == "Raptor":
            self.degree_distribution = self._ideal_soliton_dist(40)
        else:
            self.degree_distribution = self._robust_soliton_dist()
        return self.degree_distribution
    
    def messsage_packet_list(self, idx):
        random.seed(idx)
        r = random.random()
        degree = 0
        for i in range(1, len(self.degree_distribution)):
            if r < self.degree_distribution[i]:
                degree = i
                break
        degree = min(degree, self.k)
        pkg_list = random.sample(range(self.k), degree)
        return pkg_list   

class LTEncoder(LTCommon):
    def __init__(self,k):
        super().__init__(k)
        self.message_packets = []

    def set_message_packets(self, packets):
        if len(packets) != self.k:
            raise ValueError("Number of message packets should be equal to ", self.k)
        self.message_packets = packets

    def encode(self, IDs):
        if not self.message_packets:
            raise ValueError("Message packets are not set")
        if not self.degree_distribution:
            raise ValueError("Degree distribution is not set")
        coded_packets = []
        for id in IDs:
            pkg_list = self.messsage_packet_list(id)
            coded_packet = [0] * len(self.message_packets[0])
            for message_id in pkg_list:
                Matrix.vector_add_inplace(coded_packet, self.message_packets[message_id])
            coded_packets.append([id, coded_packet])
        return coded_packets

class LTDecoder(LTCommon):
    def __init__(self,k,max_ge=32):
        super().__init__(k)
        self.received_packets = []
        self.tanner_graph = []
        self.message_passing_process = []
        self.inactivation_process = []
        self.is_message_decoded = [-1] * k
        self.LU = []
        self.p = []
        self.MAX_GE = max_ge

    def set_received_packets(self, IDpackets):       
        self.received_packets = []
        self.is_message_decoded = [-1] * self.k
        self.tanner_graph = BipartiteGraph()
        self.message_passing_process = []
        for entry in IDpackets:
            self.add_received_packet(entry)

    def add_received_packet(self, IDpacket):
        index = len(self.received_packets)
        self.received_packets.append(IDpacket[1])
        message_list = self.messsage_packet_list(IDpacket[0])
        for message_idx in message_list:
            if self.is_message_decoded[message_idx] == -1:
                self.tanner_graph.add_edge(message_idx, index)
            else:
                for entry in self.message_passing_process:
                    if entry[0] == message_idx:
                        entry[2].add(index)
                        break

    def check_decoding_status(self):
        self._message_passing_decoding()
        if self.is_message_decoded.count(-1) == 0:
            return True
        return self._gaussian_elimination_decoding()

    def _message_passing_decoding(self):
        updated = True       
        while updated:
            updated = False
            right_nodes_copy = list(self.tanner_graph.right_nodes.keys())
            for coded_1 in right_nodes_copy:
                messages_coded_1 = self.tanner_graph.get_neighbors(coded_1, 'right')
                if len(messages_coded_1) == 1:
                    message = list(messages_coded_1)[0]
                    coded_to_substitute = set(self.tanner_graph.get_neighbors(message, 'left'))
                    coded_to_substitute.remove(coded_1)
                    for coded in coded_to_substitute:
                        self.tanner_graph.remove_edge(message, coded)
                    self.tanner_graph.remove_edge(message, coded_1)
                    self.message_passing_process.append((message, coded_1, coded_to_substitute))
                    self.is_message_decoded[message] = coded_1
                    updated = True

    def _gaussian_elimination_decoding(self):
        if len(self.tanner_graph.left_nodes) > self.MAX_GE: # Avoid large matrix
            return False
        if len(self.tanner_graph.left_nodes) > len(self.tanner_graph.right_nodes):
            return False
        if len(self.tanner_graph.left_nodes) < self.is_message_decoded.count(-1):
            return False
        A = self.tanner_graph.adjacency_matrix()
        p, r = LinearSol.lu_decomposition(A)
        if r < len(A[0]):
            return False
        self.LU = A
        self.p = p
        return True
    
    def _substitute_gaussian_elimination_decoding(self):
        if self.LU == []:
            return
        left_nodes = sorted(self.tanner_graph.left_nodes.keys())
        right_nodes = sorted(self.tanner_graph.right_nodes.keys())
        r = len(left_nodes)
        coded_packets = []
        for i, message in enumerate(left_nodes):
            self.is_message_decoded[message] = right_nodes[self.p[i]]
            coded_packets.append(self.received_packets[right_nodes[self.p[i]]])
        return LinearSol.lu_solve(self.LU[:r], coded_packets[:r])

    def _substitute_message_passing(self):
        for message, decoded, coded in self.message_passing_process:
            coded_packet = self.received_packets[decoded]
            for coded_idx in coded:
                Matrix.vector_add_inplace(self.received_packets[coded_idx], coded_packet)
        self.message_passing_process = []

    def get_decoded_message(self):
        self._substitute_message_passing()
        self._substitute_gaussian_elimination_decoding()
        return [[i, self.received_packets[self.is_message_decoded[i]]] for i in range(self.k) if self.is_message_decoded[i] != -1]
    
    
# Test the encode and decode functions
if __name__ == "__main__":
    encoder = LTEncoder(4)
    # Test degree distributions
    #encoder.set_degree_distribution("Soliton")
    #print("Ideal Soliton distribution:", encoder.degree_distribution)

    #encoder.set_degree_distribution("Robust Soliton")
    print("Robust Soliton distribution:", encoder.degree_distribution)
    
    message_packets = [[1, 5], [2, 6], [3, 7], [4, 8]]
    encoder.set_message_packets(message_packets)

    coded_packets = encoder.encode(range(10,20))
    print("Coded packets:")
    for packet in coded_packets:
        print(packet)

    # Test set_received_packets
    decoder = LTDecoder(4)
    print("Print degree distribution of decoder:", decoder.degree_distribution)
    indices = [1, 3, 5, 7, 9]  
    received_packets = [coded_packets[i] for i in indices]
    decoder.set_received_packets(received_packets)
    print("Received packets after set_received_packets:")
    for packet in decoder.received_packets:
        print(packet)
    print("Tanner Graph:")
    decoder.tanner_graph.print_graph()
    print("Adjacency Matrix:", decoder.tanner_graph.adjacency_matrix())

    # Test Gaussian elimination decoding
    print("\nTest Combined BP and GE:")
    if decoder.check_decoding_status() == True:
        print("Decoding is successful.")
        decoded_packets = decoder.get_decoded_message()
        print("Decoded messages:")
        for packet in decoded_packets:
            print(packet)
    else:
        print("Decoding is unsuccessful.")

    # Test set_received_packets
    print("\nNew test with 5 message packets.")
    encoder = LTEncoder(5)
    encoder.set_degree_distribution("Robust Soliton")
    print("Robust Soliton distribution:", encoder.degree_distribution)
    
    message_packets = [[1, 5], [2, 6], [3, 7], [4, 8], [5, 9]]
    encoder.set_message_packets(message_packets)

    coded_packets = encoder.encode(range(10))
    print("Coded packets:")
    for packet in coded_packets:
        print(packet)

    # Test set_received_packets
    decoder = LTDecoder(5)
    indices = [1, 3, 5, 7, 9]  
    received_packets = [coded_packets[i] for i in indices]
    decoder.set_received_packets(received_packets)
    print("Received packets after set_received_packets:")
    for packet in decoder.received_packets:
        print(packet)
    print("Adjacency Matrix:", decoder.tanner_graph.adjacency_matrix())

    # Test try_decode   
    if decoder.check_decoding_status() == True:
        print("Decoding is successful.")
        decoded_packets = decoder.get_decoded_message()
        print("Decoded messages:")
        for packet in decoded_packets:
            print(packet)
    else:
        print("Decoding is unsuccessful. Add more packets.")
    

    # Test add_received_packet
    decoder.add_received_packet(coded_packets[0])
    decoder.add_received_packet(coded_packets[8])
    print("\nReceived packets after add_received_packet:")

    # Test try_decode
    if decoder.check_decoding_status() == True:
        print("Decoding is successful.")
        decoded_packets = decoder.get_decoded_message()
        print("Decoded messages:")
        for packet in decoded_packets:
            print(packet)
    else:
        print("Decoding is unsuccessful. Add more packets.")

