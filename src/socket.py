# This is the interface recommended in `doc/sys_intro.md`

from abc import ABC, abstractmethod
from typing import Any, Optional, Tuple
from socket import AddressFamily

class Socket(ABC):
    """Abstract base class defining the interface for connection-oriented transport protocols"""
    
    @abstractmethod
    def bind(self, address: Tuple[str, int]) -> None:
        """Associate the socket with a specific local address and port
        
        Args:
            address: Local (host, port) tuple
        """
        pass

    @abstractmethod
    def connect(self, address: Tuple[str, int]) -> None:
        """Establish a connection with a remote endpoint
        
        Args:
            address: Target (host, port) tuple
        """
        pass

    @abstractmethod
    def accept(self) -> Tuple['Socket', Tuple[str, int]]:
        """Accept an incoming connection request
        
        Returns:
            Tuple of (new Socket instance, client address)
        """
        pass

    @abstractmethod
    def send(self, data: bytes, address: Optional[Tuple[str, int]] = None) -> int:
        """Send a message to the designated receiver
        
        Args:
            data: Data to be sent
            address: Target address, can be None if already connected
            
        Returns:
            Number of bytes sent
        """
        pass

    @abstractmethod
    def recv(self, size: int) -> bytes:
        """Receive a message from the socket
        
        Args:
            size: Maximum number of bytes to receive
            
        Returns:
            Received bytes
        """
        pass
    

    @abstractmethod
    def close(self) -> None:
        """Terminate connection and free resources"""
        pass


