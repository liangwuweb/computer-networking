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
    Implementation of the sending logic for sending data over a slow,
    lossy, constrained network.

    Args:
        sock -- A socket object, constructed and initialized to communicate
                over a simulated lossy network.
        data -- A bytes object, containing the data to send over the network.
    """

    logger = homework4.logging.get_logger("hw4-sender")
    logger.info("Sender started")

    chunk_size = homework4.MAX_PACKET
    offsets = range(0, len(data), chunk_size)
    chunks = [data[i : i + chunk_size] for i in offsets]

    seq_num = 0  # Initialize sequence number
    acked_seq_num = -1  # Track last acknowledged sequence number
    timeout = 0.5  # Timeout for ACK (in seconds)

    for chunk in chunks:
        packet = struct.pack("!I", seq_num) + chunk
        while seq_num > acked_seq_num:
            # Send the packet
            sock.send(packet)
            logger.info("Sent packet with sequence number: %s", seq_num)

            # Wait for ACK
            try:
                sock.settimeout(timeout)  # Set timeout for receiving ACK
                ack_data = sock.recv(4)  # Receive 4 bytes for the ACK
                ack_num = struct.unpack("!I", ack_data)[0]  # Extract the ACK number

                if ack_num == seq_num:
                    logger.info("Received ACK for packet: %s", ack_num)
                    acked_seq_num = ack_num  # Update last acknowledged sequence number
                else:
                    logger.warning("Received unexpected ACK: %s", ack_num)

            except socket.timeout:
                logger.warning("Timeout waiting for ACK for packet: %s", seq_num)
                logger.info("Retransmitting packet: %s", seq_num)

        # Move to the next packet
        seq_num += 1


def recv(sock: socket.socket, dest: io.BufferedIOBase) -> int:
    """
    Implementation of the receiving logic for receiving data over a slow,
    lossy, constrained network.

    Args:
        sock -- A socket object, constructed and initialized to communicate
                over a simulated lossy network.

    Return:
        The number of bytes written to the destination.
    """
    logger = homework4.logging.get_logger("hw4-receiver")
    logger.info("Receiver started")

    num_bytes = 0  # Total number of bytes written to the destination
    buffer = {}  # Buffer to store received packets by sequence number
    expected_seq_num = (
        0  # The next sequence number expected to be written to the destination
    )
    buffer_size = 9000  # Maximum buffer size in bytes

    while True:
        # Receive a packet
        packet = sock.recv(homework4.MAX_PACKET + 4)  # 4 bytes for sequence number
        if not packet:
            break

        # Extract sequence number and data
        (seq_num,) = struct.unpack(
            "!I", packet[:4]
        )  # First 4 bytes are the sequence number
        data = packet[4:]

        logger.info("Received packet with sequence number: %s", seq_num)

        # Store the packet in the buffer if there's space and it hasn't already been received
        if seq_num not in buffer and len(buffer) < buffer_size // homework4.MAX_PACKET:
            buffer[seq_num] = data
            logger.info("Buffered packet with sequence number: %s", seq_num)
        else:
            logger.warning(
                "Packet with sequence number %s ignored (duplicate or buffer full)",
                seq_num,
            )

        # Attempt to write packets from the buffer to the destination in order
        while expected_seq_num in buffer:
            dest.write(buffer[expected_seq_num])
            dest.flush()
            num_bytes += len(buffer[expected_seq_num])
            logger.info(
                "Written packet with sequence number: %s to destination",
                expected_seq_num,
            )
            del buffer[expected_seq_num]  # Remove the packet from the buffer
            expected_seq_num += 1

        # Send an ACK for the received packet
        ack_packet = struct.pack(
            "!I", seq_num
        )  # Send back the sequence number as the ACK
        sock.send(ack_packet)
        logger.info("Sent ACK for packet: %s", seq_num)

    return num_bytes
