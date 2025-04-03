# from GF256 import GF256
# from LinearSystem import LinearSol, Matrix
from . import GF256
from . import LinearSystem


class ReedSolomon:
    def __init__(self, n, k):
        self.n = n
        self.k = k
        self.generator_matrix = self.create_generator_matrix()
        self.generator_matrix_transpose = Matrix.transpose(self.generator_matrix) 
        self.systematic_generator_matrix = self.create_systematic_generator_matrix()
        self.systematic_generator_matrix_transpose = Matrix.transpose(self.systematic_generator_matrix) 

    def create_generator_matrix(self):
        """
        Create the generator matrix for the Reed-Solomon code. The generator matrix is given by k by n matrix 
        |--------+--------+---------+-----+-------------|
        |      1 |      1 |       1 | ... | 1           |
        |      0 |      1 |       2 | ... | n-1         |
        :        :        :         :     :             :
        |      0 |      1 | 2^{k-1} | ... | (n-1)^{k-1} |
        |--------+--------+---------+-----+-------------|
        """
        G = []
        for i in range(self.k):
            row = [GF256.exp(j, i) if i > 0 else 1 for j in range(self.n)]
            G.append(row)
        return G

    def create_systematic_generator_matrix(self):
        """
        Create the systematic generator matrix for the Reed-Solomon code. The systematic generator matrix is given by a k by n-k matrix
        """
        G = Matrix.deep_copy(self.generator_matrix)
        A = [row[:self.k] for row in G]
        LinearSol.lin_solve(A, G)
        return G

    def encode(self, message):
        return Matrix.matrix_multiply(self.generator_matrix_transpose, message)

    def encode_systematic(self, message):
        return Matrix.matrix_multiply(self.systematic_generator_matrix_transpose, message)
    
    def encode_non_systematic(self, message):
        return Matrix.matrix_multiply(self.systematic_generator_matrix_transpose[self.k+1:self.n], message)

    def decode(self, received_message, message_index):
        A = [self.generator_matrix_transpose[i] for i in message_index]
        return LinearSol.lin_solve(A, received_message)

    def decode_systematic(self, received_message, message_index):
        if len(message_index) < self.k:
            raise ValueError("The number of received packets must be at least k!")      
        # In-place reordering of received_message and message_index
        for i in range(len(message_index)):
            while message_index[i] < self.k and message_index[i] != i:
                target_index = message_index[i]
                # Swap received_message[i] with received_message[target_index]
                received_message[i], received_message[target_index] = received_message[target_index], received_message[i]
                # Swap message_index[i] with message_index[target_index]
                message_index[i], message_index[target_index] = message_index[target_index], message_index[i]
        A = [self.systematic_generator_matrix_transpose[i] for i in message_index]
        return LinearSol.lin_solve(A, received_message)

if __name__ == "__main__":
    # Parameters
    n = 7
    k = 3

    # Create Reed-Solomon encoder/decoder
    rs = ReedSolomon(n, k)

    # Test generator matrix
    print("Generator Matrix:")
    Matrix.print(rs.generator_matrix)
    print("Transpose of Generator Matrix:")
    Matrix.print(rs.generator_matrix_transpose)

    # Test encoding
    message = [[4,2], [2,6], [3,5]]
    encoded_message = rs.encode(message)
    print("Encoded Message:", encoded_message)

    # Test decoding
    idx = [3, 4, 1, 2]
    decoded_message = rs.decode([encoded_message[i] for i in idx],idx)
    print("Decoded Message:", decoded_message)

    # Test systematic generator matrix
    print("Systematic Generator Matrix:")
    Matrix.print(rs.systematic_generator_matrix)
    print("Transpose of Systematic Generator Matrix:")
    Matrix.print(rs.systematic_generator_matrix_transpose)
    # Test encoding systematic
    encoded_message = rs.encode_systematic(message)
    print("Encoded Message Systematic:", encoded_message)
    encoded_non_systematic_message = rs.encode_non_systematic(message)
    print("Encoded Message Non-Systematic:", encoded_non_systematic_message)

    # Test decoding systematic
    idx = [2,0,1]
    decoded_message = rs.decode_systematic([encoded_message[i] for i in idx],idx)
    print("Decoded Message Systematic:", decoded_message)