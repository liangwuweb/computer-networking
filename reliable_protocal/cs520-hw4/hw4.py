"""
version 1.0 
Liang Wu
"""

import socket
import io
import time
import struct
import homework4
import homework4.logging


def calculate_timeout_interval(
    sock: socket.socket, chunks: list, num_samples: int = 3
) -> float:
    """
    Calculate the initial timeout interval based on sampleRTT .

    Args:
        sock (socket.socket): The socket for communication.
        chunks (list): List of data chunks to send.
        num_samples (int): Number of RTT samples to collect.

    Returns:
        float: The calculated timeout interval.
    """
    logger = homework4.logging.get_logger("hw4-sender")
    logger.info("Calculating timeout interval based on RTT samples.")

    sent_times = {}
    sample_rtt_list = []

    for i in range(num_samples):
        if i < len(chunks):
            packet = struct.pack("!I", i) + chunks[i]
            sock.send(packet)
            logger.info("Sent packet with sequence number: %s for RTT sampling", i)
            sent_times[i] = time.time()

            try:
                sock.settimeout(1.0)  # Temporary fixed timeout for RTT sampling
                ack_data = sock.recv(4)
                ack_num = struct.unpack("!I", ack_data)[0]

                if ack_num in sent_times:
                    sample_rtt = time.time() - sent_times[ack_num]
                    sample_rtt_list.append(sample_rtt)
                    logger.info("Collected sample RTT: %s", sample_rtt)
                    del sent_times[ack_num]
            except socket.timeout:
                logger.warning("Timeout during RTT sampling for packet %s", i)

    if len(sample_rtt_list) > 0:
        estimated_rtt = sum(sample_rtt_list) / len(sample_rtt_list)
        dev_rtt = sum(abs(rtt - estimated_rtt) for rtt in sample_rtt_list) / len(
            sample_rtt_list
        )
        timeout_interval = estimated_rtt + 4 * dev_rtt
    else:
        # Fallback to default timeout
        logger.warning("RTT sampling failed. Using default timeout.")
        timeout_interval = 0.5

    return timeout_interval


def send(sock: socket.socket, data: bytes):
    """
    Implementation of the sending logic with pipelining.
    """
    logger = homework4.logging.get_logger("hw4-sender")
    logger.info("Sender started")

    chunk_size = homework4.MAX_PACKET
    offsets = range(0, len(data), chunk_size)
    chunks = [data[i : i + chunk_size] for i in offsets]

    window_size = 2  # Sliding window size
    base = 0  # base number
    next_seq_num = 0  # Next sequence number to send

    timeout_interval = calculate_timeout_interval(sock, chunks)
    logger.info("Initial timeout interval set to: %s", timeout_interval)

    # Maintain a dictionary for unacknowledged packets in the window
    unacked_packets = {}

    while base < len(chunks):
        # keep sending packets in the window
        while next_seq_num < base + window_size and next_seq_num < len(chunks):
            packet = struct.pack("!I", next_seq_num) + chunks[next_seq_num]
            sock.send(packet)
            logger.info("Sent packet with sequence number: %s", next_seq_num)
            # Add the packet to the unacknowledged dictionary
            unacked_packets[next_seq_num] = packet
            next_seq_num += 1

        # Wait for ACKs or timeout
        try:
            sock.settimeout(timeout_interval)
            ack_data = sock.recv(4)  # Receive 4 bytes for the ACK
            ack_num = struct.unpack("!I", ack_data)[0]  # Extract the ACK number

            if ack_num >= base and ack_num in unacked_packets:
                logger.info("Received ACK for packet: %s", ack_num)

                del unacked_packets[ack_num]  # Remove the acknowledged packet
                # Move the window's base forward
                while base not in unacked_packets and base < next_seq_num:
                    base += 1
        except socket.timeout:
            logger.warning("Timeout waiting for ACKs. Retransmitting window.")
            for seq_num, packet in unacked_packets.items():
                if base <= seq_num < base + window_size:
                    sock.send(packet)
                    logger.info(
                        "Retransmitted packet with sequence number: %s", seq_num
                    )

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
