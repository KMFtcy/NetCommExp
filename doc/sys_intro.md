# Project Introduction

This document introduces the purpose and general description of the project, and intends to provides high level guideline for developing.

## Overview

A transport protocol should be careful designed to fulfill different requirements such as reliable transmission, packetization and reassembly, flow control, etc.. This project mainly focus on the aspect of reliable transmission under different network conditions. We implement different shemes to support reliable transmission and compare their performance.

The rest of this document will describe the terms and definitions, common concepts and design philosophy to facilitate protocol implementation across different strategies while maintaining a consistent development style.

## Elements in Network Communication

A reliable transport protocol is supposed to run on the Internet where packets will be dropped or be late delivered with probability. Entities called **Application** use the reliable transport protocol to send and receive data to each other.

The entity that generating or receving internet packets is called **endpoint** in this system. The endpoint that sending packets is called **sender** while the one receving packets is called **receiver**.

Each sender will interact with one recevier though exchange packets. The behavior that exchange packets within a sender-recevier pair is defined by a set of rules called **protocol**. The details of protocol is implemented based on different schemes. All protocol implemented in this repo is connection-oriented, which means both participants in a sender-recevier pair will maintain some stateful information while conmunicating taking place and release them while the commucation is finished. The combination of such stateful information is called **connection**.

The data that sender wants to transmit is called **message**. The message will be divided into chunks, and data chunks are packaged by protocol as **segments**. Segment is the minimum unit processed by protocol and will be encapsulate by internet pack for transmission.

## Schemes for Reliable Transmission

The objective of reliable transmission is to solve the problem of packet loss in transmission. Two regimes of schemes are adpoted to implement reliable transmission: retransmission and erasure codes. Specifically, retransmission scheme retransmits packet when packet loss is detected, while erasure codes scheme tries to recover lossed packet with received ones.

<!-- Note that even use a erasure code scheme, retransmission will also occur when receiver is not able to recover the loss packets with inadequate receive packets. -->

Besides, different retransmission strategies also have various impacts on the metrics of communicating performance. Here, we explore two retransmission strategy: "Stop-and-Wait" and "Buffer Size with Bounded Retransmission". In Stop-and-wait strategy, the sender stops transmitting when a packet is transmitted until a ACK is received. In Buffer Size with Bounded Retransmission strategy, the retransmission of a packet occurs after one RTT without waiting for previous packets to be received.

In this project, we explore the performance of following reliable transmission implements with two retransmission strategies:

**Retransmission**

- Cumulative Acknowledgment

- Selective Acknowledgment

**Erasure Codes**

- Reed-Solomn Codes

- LT Codes

- Raptor Codes

## Protocol

Protocol is a set of rules defines the behavior of sender and receiver. Although protocols designed with different reliable transmission scheme may operate quite differently internally, they still share some common obstacles to overcome. This section discuss these common obstacles and is intended to provide protocol developers with guidance and conceptual frameworks for implementation.

### Connections

Connections provide context for communication sessions between endpoints and facilitate stateful interactions. Establishing and maintaining connections is a critical aspect of reliable protocol design.

State machine is a commonly used tools to describe the lifetime of connection. A description of state transmission provides a broad view for users to understand the workflow of protocol and forms the backbone of protocol implementation.

Handshake mechanism should be considered into design of connection-oriented transport protocol, which is the fundamental mechanism for creating and terminating connections. Parameters negotiation can be embedded in handshake for requirements of different designs.

Timeout mechanism is another commonly used machnism to protect against indefinite blocking when communication is disrupted. Timeout ensures the protocol can recover and proceed from network failures or unresponsive peers. However, the calculation of timeout is not a trivial problem. If the developer has no idea how to choose a suitable timeout value, Karn's algorithm and Jacobson's algorithm could be a good startpoint.

### Message Partition

Message partition is a general demand for transport protocol. Large message often need to be segmented into smaller units for transmission. Not only dealing with network constraints or maximum transmission unit limitations, but also partitioning according to specific protocol requirements such as dividing content into symbols for encoding and performance consideration.

Normally, message partitioning should be transparent to user, and the segments can be sent at anytime at its own convenience.

### Protocol Operations

Connection-oriented transport protocols typically provide standardized external interfaces for users. While internal implementations may vary significantly across different protocols, connection-based transport protocols generally share a core set of interfaces that offer users a consistent operational experience.

The following interfaces are recommended to form the fundamental framework for connection-oriented transport protocols:

- `connect`: Establishes a connection with a remote endpoint, handling handshaking procedures and connection state initialization.

<!-- This is typically the first operation before data transfer can begin. -->

- `listen`: Places a socket in a passive mode where it waits for incoming connection requests, essential for server-side operations.

- `accept`: Accepts an incoming connection request and creates a new socket specifically for this connection.

- `sendto`: Transmits a message to the designated receiver, handling all necessary packaging and delivery operations.

- `recv`: Listens on the endpoint and receives incoming messages from senders, managing buffering and data assembly.

- `close`: Terminates connection and free resources occupied by the protocol.

- `setsockopt`/`getsockopt`: Configures or retrieves socket options such as timeouts, buffer sizes, and protocol-specific parameters to tune performance and behavior.

- `bind`: Associates a socket with a specific local address and port, necessary for server sockets to specify where they should listen.

These interfaces provide a rational architectural foundation for protocol design. By building protocols around these core functionalities, developers can ensure their implementations both meet user expectations and maintain consistency with other transport protocols.

### Other Consideration

This section does not discuss error detection, flow control, congestion management, etc., which should no doubs be considered in pratical transport protocol. However, this project mainly focus on the impact of reliable transmission scheme on communication performance. The issues mentioned in previous sections are considered necessary to implement reliable transmission so that must be discussed, while other issues are left to developers to freely discuss and resolve in their actual implementation.
