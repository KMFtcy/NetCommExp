# from GF256 import GF256
from . import GF256
class Matrix:
    @staticmethod
    def transpose(matrix):
        """
        Transpose a matrix represented as a list of lists.
        """
        return [[row[i] for row in matrix] for i in range(len(matrix[0]))]

    @staticmethod
    def print(matrix):
        """
        Print a matrix represented as a list of lists.
        """
        for row in matrix:
            print(row)

    @staticmethod
    def deep_copy(matrix):
        """
        Create a deep copy of a matrix represented as a list of lists.
        """
        return [row[:] for row in matrix]

    @staticmethod
    def vector_add_inplace(v1, v2):
        """
        In-place vector addition in GF(256).
        v1 and v2 are lists of integers (0-255) representing vectors.
        """
        if len(v1) != len(v2):
            raise ValueError("Vectors must have the same length.")
        for i in range(len(v1)):
            v1[i] = GF256.add(v1[i], v2[i])

    @staticmethod
    def matrix_multiply(A, B):
        """
        Matrix-matrix multiplication over GF(256).
        A and B are matrices represented as lists of lists of integers (0-255).
        """
        if len(A[0]) != len(B):
            raise ValueError("Number of columns in A must be equal to number of rows in B.")        
        result = [[0] * len(B[0]) for _ in range(len(A))]
        for i in range(len(A)):
            for j in range(len(B)):
                GF256.combined_vector_operation_inplace(result[i], A[i][j], B[j])
        return result

class LinearSol:    
    @staticmethod
    def lin_solve(A, b):
        """
        Solve the linear system Ax = b.
        A is a matrix, and b is a matrx.
        """
        m, n = len(A), len(A[0])
        p, r = LinearSol.lu_decomposition(A)
        if r == n:
            b = [b[i] for i in p]
            return LinearSol.lu_solve(A[:n], b[:n])
        return None

    @staticmethod
    def lu_solve(A, b):
        """
        Solve the linear system Ax = b given the LU decomposition of A.
        """
        n = len(A)
        for j in range(n - 1):
            for i in range(j + 1, n):
                GF256.combined_vector_operation_inplace(b[i],A[i][j],b[j])
        for j in range(n - 1, -1, -1):
            GF256.scalar_vector_multiply_inplace(GF256.multiplicative_inverse(A[j][j]),b[j])
            for i in range(j - 1, -1, -1):
                GF256.combined_vector_operation_inplace(b[i], A[i][j], b[j])
        return b

    @staticmethod
    def lu_decomposition(A):
        """
        Perform LU decomposition of A. Return the permutation vector p and the rank r.
        """
        m, n = len(A), len(A[0])
        p = list(range(m))
        i = 0

        def find_pivot(i, j):
            if A[i][j] != 0:
                return True
            for k in range(i + 1, m):
                if A[k][j] != 0:
                    p[i], p[k] = p[k], p[i]
                    A[i], A[k] = A[k], A[i]
                    return True
            return False

        for j in range(n):
            if find_pivot(i, j):
                for k in range(i + 1, m):
                    l = GF256.divide(A[k][j], A[i][j])
                    A[k][j] = 0
                    A[k][i] = l
                    A[k][j+1:n] = GF256.combined_vector_operation(A[k][j+1:n], l, A[i][j+1:n])
                i += 1
                if i == m:
                    break

        r = i
        return p, r

if __name__ == "__main__":
    # Test LU Decomposition
    A = [
        [1, 2, 3],
        [4, 5, 6],
        [7, 8, 9]
    ]
    p, r = LinearSol.lu_decomposition(A)
    print("LU Decomposition:")
    print("p:", p)
    print("r:", r)
    print("A:", A)

    # Test LU Solve
    A = [
        [1, 2, 3],
        [0, 1, 4],
        [0, 0, 1]
    ]
    b = [[6], [5], [4]]
    x = LinearSol.lu_solve(A, b)
    print("LU Solve:")
    print("x:", x)

    # Test Linear Solve
    A = [
        [1, 2, 3],
        [4, 5, 6],
        [7, 8, 9]
    ]
    x = [[6,2], [15,4], [24,1]]
    b = Matrix.matrix_multiply(A, x)
    print("b", b)
    print("A:")
    Matrix.print(A)
    print("x:")
    Matrix.print(x)
    y = LinearSol.lin_solve(A, b)
    print("decoded x:")
    Matrix.print(b)
    print("A:")
    Matrix.print(A)

    # Test Matrix Multiply
    A = [
        [1, 2],
        [3, 4]
    ]
    B = [
        [5, 6],
        [7, 8]
    ]
    result = Matrix.matrix_multiply(A, B)
    print("AB:")
    Matrix.print(result)