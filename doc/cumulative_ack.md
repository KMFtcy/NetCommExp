# Specification of Cumulative ACK Protocol

This documents specifies the design of Cumulative ACK Protocol, which is a implementation of end-to-end reliable transmission protocol based on UDP. The concepts and definations about reliable transmission protocol and other related elements are described in [sys_intro.md](./sys_intro.md), and also adopted in this document.

Cumulative ACK Protocol is a unicast data transfer protocol, which is intended to provide insights into developiment of reliable transmission protocols for developers. Thus, The implementation should be consice and clear as possible, which means only the most necesssary mechanism is adopted and implemented in this protocol.

It is worth to mention that, while Cumulative ACK Protocol only supports unicast transmission, which will simplify the handshake mechanism of connection termination, it is supposed to be easily extended to support bidirectional communication.

In terms of reliable transmission, Cumulative ACK Protocol adopts retransmission with cumulative ACK to handle packet loss. The retransmission strategy is buffer-size-and-bounded-retransmission as decribes in [sys_intro.md](./sys_intro.md).

The following machnisms are considered besides the reliable transmission scheme:

- Message Partition and Reassembly
- Handshake
- Timeout

## Model of Operation

### Sender Operation

The application first creates an instance of Cumulative ACK Protocol, which serves as a socket for message transmission.

The socket must establish a connection with the receiver's socket. During this process, Cumulative ACK Protocol performs a three-way handshake to establish the connection.

Once the connection is established, the application transmits messages by invoking protocol-provided interfaces and passing data buffers as parameters. Cumulative ACK Protocol segments the message and transmits each segment separately. Retransmission and timeout mechanisms are employed to ensure transmission reliability.

When all messages have been transmitted, the application may terminate the connection by invoking the provided interface. Cumulative ACK Protocol performs a handshake to terminate the connection.

### Receiver Operation

The application first creates an instance of Cumulative ACK Protocol, similar to the sender.

The socket must be placed in listen mode for receiving messages. Concurrently, a buffer must be provided for storing received messages. Subsequently, the application blocks until a message is received.

The socket automatically performs a handshake with the sender upon receiving a connection attempt segment. Message segments are then received in sequence and reassembled into complete messages in the provided buffer.

When a message has been successfully reassembled, the protocol notifies the application.

When the application wishes to terminate the connection, it invokes the provided interface. Cumulative ACK Protocol performs a handshake to terminate the connection.

## Connections

### States of Connection

### Establishment of Connection

### Termination of Connection

## Segment Format

