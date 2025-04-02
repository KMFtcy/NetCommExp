import random
from copy import deepcopy
from LinearSystem import Matrix, LinearSol

class RandomLinearCode:
    def __init__(self, k):
        self.k = k
        self.message_packets = []
        self.received_packets = []
        self.generator_matrix_dec = []
        self.LU = []
        self.p = []
        self.r = 0

    def set_message_packets(self, packets):
        if len(packets) != self.k:
            raise ValueError("Number of message packets should be equal to ", self.k)
        self.message_packets = packets

    def encode(self, indexrange):
        if not self.message_packets:
            raise ValueError("Message packets are not set")
        generator_matrix = self.generate_matrix(indexrange)
        return Matrix.matrix_multiply(generator_matrix, self.message_packets)

    def generate_matrix(self, indexrange):
        matrix = []
        for i in indexrange:
            random.seed(i)
            matrix.append([random.randint(0, 255) for _ in range(self.k)])
        return matrix

    def set_received_packets(self, packets, indices):
        self.received_packets = packets
        self.generator_matrix_dec = self.generate_matrix(indices)

    def add_received_packet(self, packet, index):
        self.received_packets.append(packet)
        self.generator_matrix_dec.append(self.generate_matrix([index]))

    def rank(self):
        self.LU = deepcopy(self.generator_matrix_dec)
        self.p, self.r = LinearSol.lu_decomposition(self.LU)
        return self.r
    
    def decode(self):
        if len(self.received_packets) < self.k:
            raise ValueError("Not enough coded packets to decode")
        if self.r == self.k:
            self.received_packets = [self.received_packets[i] for i in self.p]
            return LinearSol.lu_solve(self.LU[:self.k], self.received_packets[:self.k])
        else:
            return LinearSol.lin_solve(self.generator_matrix_dec, self.received_packets)

# Test the encode and decode functions
if __name__ == "__main__":
    rlc = RandomLinearCode(4)
    message_packets = [[1, 5], [2, 6], [3, 7], [4, 8]]
    rlc.set_message_packets(message_packets)
    
    indexrange = range(10, 15)
    coded_packets = rlc.encode(indexrange)
    print("Coded packets:")
    Matrix.print(coded_packets)
    
    rlc.set_received_packets(coded_packets, indexrange)
    print("Rank of the generator matrix:", rlc.rank())  
    decoded_packets = rlc.decode()
    print("Decoded packets:")
    Matrix.print(decoded_packets)



