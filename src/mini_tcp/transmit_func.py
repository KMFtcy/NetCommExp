from typing import Callable, Optional, Tuple, Union, Any
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Type for the transmit function - it should take bytes and an address tuple and return number of bytes sent
TransmitFuncType = Callable[[bytes], int]

# Global transmit function reference
transmit_func_call: Optional[TransmitFuncType] = None

def set_transmit_func_call(target: TransmitFuncType) -> None:
    """Set the transmit function to be used by the transport layer.
    """
    global transmit_func_call
    transmit_func_call = target
    logger.debug("Transmit function has been set")

def transmit(data: bytes) -> int:
    """Transmit data to the specified address using the configured transmit function.

    Args:
        data: The bytes to transmit
        address: Tuple of (host, port) to send to

    Returns:
        Number of bytes transmitted

    Raises:
        RuntimeError: If no transmit function has been configured
    """
    if transmit_func_call is None:
        raise RuntimeError("No transmit function configured. Call set_transmit_func_call first.")

    try:
        bytes_sent = transmit_func_call(data)
        logger.debug(f"Transmitted {bytes_sent} bytes")
        return bytes_sent
    except Exception as e:
        logger.error(f"Error during transmission: {str(e)}")
        raise

