# Wrap32 is a class that represents a 32-bit segment integer that has been wrapped around a 64-bit absolute sequence number
class Wrap32:
    def __init__(self, raw_value):
        self.raw_value = raw_value & 0xFFFFFFFF  # Ensure it's a 32-bit unsigned integer
    
    @staticmethod
    def wrap(n, zero_point):
        """
        Construct a Wrap32 object based on absolute sequence number n and zero point
        """
        wrapped_value = (zero_point.raw_value + (n & 0xFFFFFFFF)) & 0xFFFFFFFF
        return Wrap32(wrapped_value)
    
    def unwrap(self, zero_point, checkpoint):
        """
        Returns an absolute sequence number that corresponds to the current Wrap32 value
        under the given zero point condition and is closest to the given checkpoint.
        
        Args:
            zero_point: Wrap32 object representing the zero point
            checkpoint: 64-bit absolute sequence number used as a reference point
            
        Returns:
            64-bit absolute sequence number corresponding to the current Wrap32,
            which is closest to the checkpoint
        """
        tmp = 0
        tmp1 = 0
        n_minus_isn = self.raw_value - zero_point.raw_value
        if n_minus_isn < 0:
            tmp = n_minus_isn + (1 << 32)
        else:
            tmp = n_minus_isn
        
        # if tmp is greater than or equal to checkpoint, return tmp
        if tmp >= checkpoint:
            return tmp
        
        # calculate the high 32 bits
        tmp |= ((checkpoint >> 32) << 32)
        
        # find the smallest value greater than checkpoint
        while tmp <= checkpoint:
            tmp += (1 << 32)
        
        # calculate the value smaller than tmp by 2^32
        tmp1 = tmp - (1 << 32)
        
        # return the value closest to checkpoint
        return tmp1 if (checkpoint - tmp1 < tmp - checkpoint) else tmp
    
    def __add__(self, n):
        """
        Implement Wrap32 + integer operation
        """
        return Wrap32((self.raw_value + (n & 0xFFFFFFFF)) & 0xFFFFFFFF)
    
    def __eq__(self, other):
        return self.raw_value == other.raw_value
    
    def __repr__(self):
        return f"Wrap32({self.raw_value})"