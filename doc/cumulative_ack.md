# Specification of Cumulative ACK Protocol

This documents specifies the design of Cumulative ACK Protocol (CAP), which is a implementation of end-to-end reliable transmission protocol based on UDP. The concepts and definations about reliable transmission protocol and other related elements are described in [sys_intro.md](./sys_intro.md), and also adopted in this document.

CAP is a unicast data transfer protocol, which is intended to provide insights into developiment of reliable transmission protocols for developers. Thus, The implementation should be consice and clear as possible, which means only the most necesssary mechanism is adopted and implemented in this protocol.

It is worth to mention that, while CAP only supports unicast transmission, which will simplify the handshake mechanism of connection termination, it is supposed to be easily extended to support bidirectional communication.

In terms of reliable transmission, CAP adopts retransmission with cumulative ACK to handle packet loss. The retransmission strategy is buffer-size-and-bounded-retransmission as decribes in [sys_intro.md](./sys_intro.md).

The following machnisms are considered besides the reliable transmission scheme:

- Message Partition and Reassembly
- Handshake
- Timeout

## Model of Operation

### Sender Operation

The application first creates an instance of CAP, which serves as a socket for message transmission.

The socket must establish a connection with the receiver's socket. During this process, CAP performs a three-way handshake to establish the connection.

Once the connection is established, the application transmits messages by invoking protocol-provided interfaces and passing data buffers as parameters. CAP segments the message and transmits each segment separately. Retransmission and timeout mechanisms are employed to ensure transmission reliability.

When all messages have been transmitted, the application may terminate the connection by invoking the provided interface. CAP performs a handshake to terminate the connection.

### Receiver Operation

The application first creates an instance of CAP, similar to the sender.

The socket must be placed in listen mode for receiving messages. Concurrently, a buffer must be provided for storing received messages. Subsequently, the application blocks until a message is received.

The socket automatically performs a handshake with the sender upon receiving a connection attempt segment. Message segments are then received in sequence and reassembled into complete messages in the provided buffer.

When a message has been successfully reassembled, the protocol notifies the application.

When the application wishes to terminate the connection, it invokes the provided interface. CAP performs a handshake to terminate the connection.

## Connection

Connection is a stateful information that is maintained by both sender and receiver. It is used to record the status of the communication and the message being transmitted. A connection is considered to be established if and only if the sender and receiver have completed the handshake to exchange the connection parameters.

CAP is a connection-oriented protocol, which means a connection must be established before any message transmission. During the communication, a CAP connection progresses through a series of states until termination.

This section describes the state of a CAP connection, and the behavior through the lifetime of a connection.

### States

CAP connection goes through three phases of initialization, data transfer, and termination. There are eight possible states as follows:

- **CLOSED**: Initial state, connection is closed
- **LISTEN**: Receiver waiting for connection request
- **SYN_SENT**: Sender has sent connection request
- **SYN_RCVD**: Receiver has received and responded to connection request
- **ESTABLISHED**: Connection established, data transfer enabled
- **FIN_WAIT**: Sender requesting connection termination
- **CLOSE_WAIT**: Receiver has received termination request
- **TIME_WAIT**: Waiting for all packets to expire

The state of CAP connections transmit depend on segment. The following diagram shows the expected state transition of CAP connections:

```
   Sender State                             Receiver State
        CLOSED                                   LISTEN
   1.   SYN_SENT   -->        SYN          -->
   2.              <--      SYN+ACK        <--   SYN_RCVD
   3.  ESTABLISHED -->        DataAck      -->
   4.              <->     Data,DataAck    <->   ESTABLISHED
   5.              -->        FIN          -->
   6.   FIN_WAIT   <--      FIN+ACK        <--   CLOSE_WAIT
   7.   TIME_WAIT  -->        ACK          -->
   8.     CLOSED   <--      (timeout)      <--     CLOSED
```

## Segment

CAP segments implement the function of reliable transmission. Each CAP segment carries a sequence number to detect the losses of packets. Unlike TCP, the CAP sequence numbers increment by one per packet.

Based on the lifetime of a connection, the segment types are defined as follows:
- **SYN**: First segment in three-way handshake, sent by client to initiate connection, contains initial sequence number
- **SYN-ACK**: Second segment in three-way handshake, sent by server in response to SYN, contains server's sequence number and acknowledges client's SYN
- **Data**: Carries application data payload with a sequence number for ordering and reassembly
- **DataAck**: Combines data transmission with acknowledgment functionality, improving protocol efficiency
- **FIN**: Indicates sender has finished sending data, initiates connection termination
- **FIN-ACK**: Acknowledges receipt of FIN and indicates sender also wishes to terminate connection

CAP segments are sent as UDP datagrams, which consists of a header and a payload. The header of CAP segments follows the UDP header and describe information specific to CAP.

### Header

The CAP segment header contains essential control information for protocol operation. Each field in the header serves a specific purpose in managing reliable data transmission and connection control.

The header consists of the following fields:

| Field | Size (bits) | Description |
|-------|-------------|-------------|
| Type | 4 | Identifies the segment type: <br> - 0x01: SYN (Connection request) <br> - 0x02: SYN-ACK (Connection acknowledgment) <br> - 0x03: Data (Data segment) <br> - 0x04: DataAck (Data with acknowledgment) <br> - 0x05: FIN (Connection termination) <br> - 0x06: FIN-ACK (Termination acknowledgment) |
| Reserved | 28 | Reserved for future protocol extensions.|
| Sequence Number | 32 | Uniquely identifies each segment in transmission order. Initialized to a random value during connection setup and increments by one for each subsequent segment. |
| Ack Number | 32 | Indicates the next expected sequence number, acknowledging all segments up to (Ack Number - 1). Valid in SYN-ACK, DataAck, and FIN-ACK segments. |

The header format in bits shows below:

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|Type |                         Reserved                          |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                        Sequence Number                          |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                         Ack Number                             |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```
