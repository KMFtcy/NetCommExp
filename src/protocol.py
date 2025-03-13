# This is the interface recommended in `doc/sys_intro.md`

from abc import ABC, abstractmethod
from typing import Any, Optional, Tuple
from socket import AddressFamily

class Protocol(ABC):
    """Abstract base class defining the interface for connection-oriented transport protocols"""
    
    @abstractmethod
    def connect(self, address: Tuple[str, int]) -> None:
        """Establish a connection with a remote endpoint
        
        Args:
            address: Target (host, port) tuple
        """
        pass

    @abstractmethod
    def listen(self, backlog: int = 1) -> None:
        """Put the socket in passive mode, waiting for incoming connection requests
        
        Args:
            backlog: Maximum number of pending connection requests
        """
        pass

    @abstractmethod
    def accept(self) -> Tuple['Protocol', Tuple[str, int]]:
        """Accept an incoming connection request
        
        Returns:
            Tuple of (new Protocol instance, client address)
        """
        pass

    @abstractmethod
    def sendto(self, data: bytes, address: Optional[Tuple[str, int]] = None) -> int:
        """Send a message to the designated receiver
        
        Args:
            data: Data to be sent
            address: Target address, can be None if already connected
            
        Returns:
            Number of bytes sent
        """
        pass

    @abstractmethod
    def recv(self, bufsize: int) -> bytes:
        """Receive incoming messages from senders
        
        Args:
            bufsize: Size of receive buffer
            
        Returns:
            Received data
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Terminate connection and free resources"""
        pass

    @abstractmethod
    def setsockopt(self, level: int, optname: str, value: Any) -> None:
        """Configure socket options
        
        Args:
            level: Protocol level
            optname: Option name
            value: Option value
        """
        pass

    @abstractmethod
    def getsockopt(self, level: int, optname: str) -> Any:
        """Retrieve socket options
        
        Args:
            level: Protocol level
            optname: Option name
            
        Returns:
            Option value
        """
        pass

    @abstractmethod
    def bind(self, address: Tuple[str, int]) -> None:
        """Associate the socket with a specific local address and port
        
        Args:
            address: Local (host, port) tuple
        """
        pass

