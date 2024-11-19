"""
Where solution code to hw4 should be written.  No other files should
be modified.
"""

import socket
import io
import time
import typing
import struct
import homework4
import homework4.logging


def send(sock: socket.socket, data: bytes):
    """
    Implementation of the sending logic with pipelining.
    """
    logger = homework4.logging.get_logger("hw4-sender")
    logger.info("Sender started")

    chunk_size = homework4.MAX_PACKET
    offsets = range(0, len(data), chunk_size)
    chunks = [data[i : i + chunk_size] for i in offsets]

    window_size = 5  # Sliding window size
    base = 0  # base number
    next_seq_num = 0  # Next sequence number to send
    timeout = 0.5  # Timeout for retransmissions
    acked = set()  # Track acknowledged packets

    while base < len(chunks):
        # keep sending packets in the window
        while next_seq_num < base + window_size and next_seq_num < len(chunks):
            packet = struct.pack("!I", next_seq_num) + chunks[next_seq_num]
            sock.send(packet)
            logger.info("Sent packet with sequence number: %s", next_seq_num)
            next_seq_num += 1

        # Wait for ACKs or timeout
        try:
            sock.settimeout(timeout)
            ack_data = sock.recv(4)  # Receive 4 bytes for the ACK
            ack_num = struct.unpack("!I", ack_data)[0]  # Extract the ACK number

            if ack_num not in acked and ack_num >= base:
                logger.info("Received ACK for packet: %s", ack_num)
                acked.add(ack_num)

                # Move the window's base forward
                while base in acked:
                    base += 1
        except socket.timeout:
            logger.warning("Timeout waiting for ACKs. Retransmitting window.")
            for i in range(base, min(base + window_size, len(chunks))):
                packet = struct.pack("!I", i) + chunks[i]
                sock.send(packet)
                logger.info("Retransmitted packet with sequence number: %s", i)

    logger.info("All data sent successfully")


def recv(sock: socket.socket, dest: io.BufferedIOBase) -> int:
    """
    Implementation of the receiving logic with pipelining.
    """
    logger = homework4.logging.get_logger("hw4-receiver")
    logger.info("Receiver started")

    num_bytes = 0  # Total bytes written to destination
    buffer = {}  # Buffer for out-of-order packets
    expected_seq_num = 0  # Sequence number expected for writing

    while True:
        try:
            # Receive a packet
            packet = sock.recv(homework4.MAX_PACKET + 4)
            if not packet:
                break

            # Extract sequence number and data
            (seq_num,) = struct.unpack("!I", packet[:4])
            data = packet[4:]

            logger.info("Received packet with sequence number: %s", seq_num)

            # Buffer packets if they are not the expected one
            if seq_num not in buffer and seq_num >= expected_seq_num:
                buffer[seq_num] = data
                logger.info("Buffered packet with sequence number: %s", seq_num)

            # Send an ACK for the received packet
            ack_packet = struct.pack("!I", seq_num)
            sock.send(ack_packet)
            logger.info("Sent ACK for packet: %s", seq_num)

            # Write packets in order from the buffer
            while expected_seq_num in buffer:
                dest.write(buffer[expected_seq_num])
                dest.flush()
                num_bytes += len(buffer[expected_seq_num])
                del buffer[expected_seq_num]
                expected_seq_num += 1

        except socket.error as e:
            logger.error("Error receiving data: %s", e)
            break

    return num_bytes
