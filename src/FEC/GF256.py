class GF256:
    # Irreducible polynomial for GF(256): x^8 + x^4 + x^3 + x + 1
    IRREDUCIBLE_POLY = 0x11B  # Binary: 100011011
    # Precompute multiplication and inverse tables
    MULT_TABLE = [[0] * 256 for _ in range(256)]  # Multiplication table
    INV_TABLE = [0] * 256  # Multiplicative inverse table

    @staticmethod
    def _init_tables():
        for a in range(256):
            for b in range(256):
                # Compute a * b in GF(256)
                result = 0
                temp_a = a  # Temporary variable for a
                temp_b = b  # Temporary variable for b
                for _ in range(8):
                    if temp_b & 1:  # If the least significant bit of b is set
                        result ^= temp_a  # Add a to the result
                    carry = temp_a & 0x80  # Check if the highest bit of a is set
                    temp_a <<= 1  # Multiply a by x
                    if carry:  # If there was a carry, reduce modulo IRREDUCIBLE_POLY
                        temp_a ^= GF256.IRREDUCIBLE_POLY
                    temp_b >>= 1  # Divide b by x
                GF256.MULT_TABLE[a][b] = result

        # Compute multiplicative inverses
        for a in range(1, 256):  # Skip 0, as it has no inverse
            for x in range(1, 256):
                if GF256.multiply(a, x) == 1:
                    GF256.INV_TABLE[a] = x
                    break

    @staticmethod
    def add(a, b):
        return a ^ b

    @staticmethod
    def subtract(a, b): return GF256.add(a, b)

    @staticmethod
    def multiply(a, b): return GF256.MULT_TABLE[a][b]

    @staticmethod
    def divide(a, b):
        if b == 0:
            raise ValueError("Division by zero is not allowed.")
        return GF256.multiply(a, GF256.multiplicative_inverse(b))

    @staticmethod
    def multiplicative_inverse(a):
        if a == 0:
            raise ValueError("Zero has no multiplicative inverse.")
        return GF256.INV_TABLE[a]

    @staticmethod
    def exp(base, exponent):
        """
        Compute the exponentiation in GF(256).
        """
        result = 1
        while exponent > 0:
            if exponent & 1:
                result = GF256.multiply(result, base)
            base = GF256.multiply(base, base)
            exponent >>= 1
        #for _ in range(exponent):
        #    result = GF256.multiply(result, base)
        return result

    @staticmethod
    def vector_add(v1, v2):
        """
        Vector addition in GF(256).
        v1 and v2 are lists of integers (0-255) representing vectors.
        """
        if len(v1) != len(v2):
            raise ValueError("Vectors must have the same length.")
        return [GF256.add(v1[i], v2[i]) for i in range(len(v1))]

    @staticmethod
    def scalar_vector_multiply(scalar, vector):
        """
        Scalar-vector multiplication in GF(256).
        scalar is an integer (0-255), and vector is a list of integers (0-255).
        """
        return [GF256.multiply(scalar, x) for x in vector]

    @staticmethod
    def scalar_vector_multiply_inplace(scalar, vector):
        """
        In-place scalar-vector multiplication in GF(256).
        scalar is an integer (0-255), and vector is a list of integers (0-255).
        """
        for i in range(len(vector)):
            vector[i] = GF256.multiply(scalar, vector[i])

    @staticmethod
    def combined_vector_operation(x, alpha, y):
        """
        Compute x + alpha * y where x and y are vectors, and alpha is a scalar in GF(256).
        """
        if len(x) != len(y):
            raise ValueError("Vectors must have the same length.")
        return [GF256.add(x[i], GF256.multiply(alpha, y[i])) for i in range(len(x))]

    @staticmethod
    def combined_vector_operation_inplace(x, alpha, y):
        """
        In-place computation of x + alpha * y where x and y are vectors, and alpha is a scalar in GF(256).
        """
        if len(x) != len(y):
            raise ValueError("Vectors must have the same length.")
        for i in range(len(x)):
            x[i] = GF256.add(x[i], GF256.multiply(alpha, y[i]))

    # Initialize the tables when the class is loaded
GF256._init_tables()

# Example usage
if __name__ == "__main__":
    a = 87  # Example element
    b = 131  # Example element

    print(f"a = {a}")
    print(f"b = {b}")

    # Addition
    c = GF256.add(a, b)
    print(f"a + b = {c}")

    # Multiplication
    d = GF256.multiply(a, b)
    print(f"a * b = {d}")

    # Division
    e = GF256.divide(a, b)
    print(f"a / b = {e}")

    # Multiplicative inverse
    inv_a = GF256.multiplicative_inverse(a)
    print(f"Multiplicative inverse of a = {inv_a}")

    # Example vectors in GF(256)
    v1 = [0x57, 0x83, 0x1B, 0xC1]
    v2 = [0x13, 0xAA, 0x4F, 0x2D]

    # Scalar in GF(256)
    scalar = 0x1B

    print(f"v1 = {v1}")
    print(f"v2 = {v2}")
    print(f"scalar = {scalar}")

    # Vector addition
    v_add = GF256.vector_add(v1, v2)
    print(f"v1 + v2 = {v_add}")

    # Scalar-vector multiplication
    v_scalar_mult = GF256.scalar_vector_multiply(scalar, v2)
    print(f"scalar * v2 = {v_scalar_mult}")

    # Inplace scalar-vector multiplication
    GF256.scalar_vector_multiply_inplace(scalar, v2)
    print(f"v2 (after inplace scalar multiplication) = {v2}")

    # Example vectors and scalar for combined vector operation
    x = [0x57, 0x83, 0x1B, 0xC1]
    y = [0x13, 0xAA, 0x4F, 0x2D]
    alpha = 0x1B

    # Combined vector operation
    combined_result = GF256.combined_vector_operation(x, alpha, y)
    print(f"x + alpha * y = {combined_result}")

    # In-place combined vector operation
    GF256.combined_vector_operation_inplace(x, alpha, y)
    print(f"x (after in-place operation) = {x}")
