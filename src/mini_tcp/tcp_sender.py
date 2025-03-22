from src.mini_tcp.transmit_func import transmit
from src.util.byte_stream import ByteStream
from src.mini_tcp.wrapping_intergers import Wrap32
from src.mini_tcp.tcp_message import TCPReceiverMessage, TCPSenderMessage
from collections import deque
from src.mini_tcp.tcp_config import MAX_PAYLOAD_SIZE, MAX_SEQNO

class TcpSender:
    def __init__(self, input_stream: ByteStream, isn: Wrap32, initial_RTO: int):
        self.input_stream = input_stream
        self.isn = isn
        self.initial_RTO = initial_RTO
        self.RTO = initial_RTO
        self.retrans_count = 0
        self.fin_seqno = MAX_SEQNO
        self.next_seqno = 0
        self.ack_seqno = 0
        self.ack_received = False
        self.window_size = 1
        self.last_sent_time = 0
        self.outstanding_data = deque()
        self.syn_sent = False
        self.fin_sent = False
        self.recv_zero_window_size = False # we need to probe if we receive a zero window size


    def receive(self, message: TCPReceiverMessage):
        # if RST is set, set the stream error
        if message.RST:
            self.input_stream.set_error()
        
        # update window size
        if message.window_size:
            window_size = message.window_size
            self.recv_zero_window_size = False
        else:
            self.recv_zero_window_size = True

        # handle correct message
        if message.ackno:
            new_ack_seqno = message.ackno.unwrap(self.isn, self.ack_seqno)
            # ignore message greater than the next sequence number
            if new_ack_seqno > self.next_seqno:
                self.ack_seqno = new_ack_seqno

            # if new ackno is greater than ackno, update the ackno
            if new_ack_seqno > self.ack_seqno:
                self.ack_seqno = new_ack_seqno
                # pop segments that have been acknowledged
                while len(self.outstanding_data):
                    segment = self.outstanding_data[0]
                    if segment.seqno.unwrap(self.isn, self.ack_seqno) + segment.squence_length() <= self.ack_seqno:
                        self.outstanding_data.popleft()
                    else:
                        break
                # reset the timer
                self.reset_timer()
            
            # if the ackno is not greater, but the window_size is expanded for more segments, update window size
            if new_ack_seqno <= self.ack_seqno and message.window_size + new_ack_seqno > self.window_size + self.ack_seqno:
                self.window_size = new_ack_seqno + message.window_size - self.ack_seqno


    def push(self):
        while self.window_size > 0 and self.next_seqno < self.ack_seqno + self.window_size:
            msg = TCPSenderMessage()

            # set the sequence number
            msg.seqno = self.isn + self.next_seqno

            # if it's the first message, set the SYN flag
            if self.next_seqno == 0:
                msg.SYN = True
                self.syn_sent = True

            # if stream has error, set the RST flag
            if self.input_stream.error:
                msg.RST = True

            # calculate the payload size
            payload_size = min(self.window_size - (self.next_seqno - self.ack_seqno) - msg.SYN, MAX_PAYLOAD_SIZE)
            payload_size = min(payload_size, self.input_stream.bytes_buffered())

            # filled the payload
            msg.payload = self.input_stream.peek(payload_size)
            self.input_stream.pop(payload_size)

            # check if we can send a FIN
            if self.input_stream.is_finished() and self.next_seqno + payload_size<= self.ack_seqno + self.window_size and self.fin_seqno == MAX_SEQNO:
                msg.FIN = True
                self.fin_sent = True
                self.fin_seqno = self.next_seqno + payload_size + msg.SYN + msg.FIN

            # avoid sending a empty message
            if msg.squence_length() == 0:
                break

            # send a message
            transmit(msg)
            self.outstanding_data.append(msg)

            # update the next sequence number,
            # if the FIN has been addedd to next_seqno, don't add it again
            self.next_seqno += min(self.next_seqno + msg.squence_length(), self.fin_seqno)

            # if FIN break the loop
            if msg.FIN:
                break

    def tick(self, ms_since_last_tick: int):
        # when queue is empty, reset the timer and return
        if len(self.outstanding_data) == 0:
            self.reset_timer()
            return

        # if we have outstanding data, handler tick
        self.last_sent_time += ms_since_last_tick
        if self.last_sent_time >= self.RTO:
            # if window size in receiver is 0, we need to probe
            if self.recv_zero_window_size:
                transmit(self.outstanding_data[0])
                self.reset_timer()
                return
            # else send the timeout message and update the RTO
            transmit(self.outstanding_data[0])
            self.last_sent_time = 0
            self.retrans_count += 1
            self.RTO *= 2


    def reset_timer(self):
        self.last_sent_time = 0
        self.RTO = self.initial_RTO
        self.retrans_count = 0

    def make_empty_message(self) -> TCPSenderMessage:
        msg = TCPSenderMessage()
        msg.seqno = self.isn + min(self.next_seqno, self.fin_seqno)
        # if the stream has error, set the RST flag
        if self.input_stream.has_error():
            msg.RST = True
        return msg

