import sys
import socket
import struct
import threading
import time


class STPNode:
    def __init__(self, node_id, weight, port):
        self.node_id = node_id
        self.weight = weight
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", self.port))
        self.received_acks = set()  # Track connection acks
        self.running = True
        self.known_ports = [5001, 5002, 5003]  # Maintain per-node port list
        self.mode = "default"
        self.received_connections = set()
        self.received_bpdu = set()
        self.root = True
        self.connection_complete = (
            threading.Event()
        )  # Event to signal connection completion

        self.bpdu = [node_id, weight, port]
        print(f"Node {self.node_id} initialized on port {self.port}")

    def set_running(self, value: bool):
        """
        setter for running
        """
        self.running = value

    def connect(self):
        """
        Establish connections with other nodes before broadcasting.
        Continuously send connection messages until all acknowledgments are received.
        """
        print(f"Node {self.node_id} starting connection phase.")
        message_type = 2  # 2 indicates a connection message
        packed_data = struct.pack("!III", message_type, self.weight, self.node_id)

        while len(self.received_acks) < 2:
            # Send connection message to all other known ports
            for target_port in self.known_ports[:]:
                if target_port != self.port:
                    self.sock.sendto(packed_data, ("127.0.0.1", target_port))
                    print(
                        f"Sent connection message to port {target_port}: {packed_data}"
                    )

            # Short sleep to avoid overwhelming the network
            time.sleep(0.5)

        print(
            f"\033[92mNode {self.node_id} received all connection acks. Ready to broadcast.\033[0m"
        )
        self.connection_complete.set()  # Signal connection phase is complete

    def reset_known_port(self):
        """
        reset known port
        """
        self.known_ports = [5001, 5002, 5003]

    def broadcast(self):
        """
        Periodically broadcast this node's ID and weight to all other nodes.
        """
        print(self.known_ports)
        self.reset_known_port()
        print(self.known_ports)
        print(self.running)
        print(f"Node {self.node_id} broadcasting BPDU messages...")
        # while self.running:
        message_type = 0  # 0 indicates a BPDU message
        packed_data = struct.pack("!III", message_type, self.weight, self.node_id)

        for target_port in self.known_ports:
            if target_port != self.port:
                self.sock.sendto(packed_data, ("127.0.0.1", target_port))
                print(f"Broadcasted BPDU to port {target_port}: {packed_data}")

            # time.sleep(2)  # Broadcast every 2 seconds

    def election(self, other_id, other_weight, addr):
        """
        Initial Election Process
        """
        # bpdu[0] -> node_id, bpdu[1] -> weight
        if (self.bpdu[0] + self.bpdu[1]) > (other_id + other_weight):
            self.root = False
            self.bpdu = [other_id, other_weight, addr[1]]

    def listen(self):
        """
        Listen for incoming messages from other nodes.
        """
        while self.running:
            try:
                data, addr = self.sock.recvfrom(1024)  # Buffer size is 1024 bytes
                print(f"Node {self.node_id} received data from {addr}: {data}")

                # Unpack the first field (message_type) to determine the format
                message_type = struct.unpack("!I", data[:4])[0]

                if message_type == 2:  # Connection message
                    message_type, weight, sender_id = struct.unpack("!III", data)
                    if sender_id not in self.received_connections:
                        self.received_connections.add(sender_id)
                        print(f"Received connection request from {addr}.")
                        # Send acknowledgment back
                        ack_data = struct.pack("!III", 3, self.weight, self.node_id)
                        self.sock.sendto(ack_data, addr)
                        print(f"Sent connection ack to {addr}")

                elif message_type == 3:  # Connection acknowledgment
                    message_type, weight, sender_id = struct.unpack("!III", data)
                    target_port = addr[1]  # Extract the sender's port
                    print(f"Received connection ack from {addr}.")
                    self.received_acks.add(target_port)
                    if target_port in self.known_ports:
                        self.known_ports.remove(target_port)

                elif message_type == 0:  # BDPU message
                    self.connection_complete.wait()  # Wait for connection phase to complete
                    message_type, weight, sender_id = struct.unpack("!III", data)
                    if sender_id not in self.received_bpdu:
                        self.received_bpdu.add(sender_id)
                        print(
                            f"Received BPDU message from {addr}: weight={weight}, sender_id={sender_id}"
                        )
                        self.election(sender_id, weight, addr)
                        print(f"Current Root: {self.bpdu}")

                if len(self.received_bpdu) == 2:
                    self.running = False
            except Exception as e:
                print(f"Error in listening: {e}")

    def hello(self):
        """
        Exchange hello messges
        """
        print(f"Node {self.node_id} is not the root. sending hello messages")
        while self.running:
            # Create a simple message combining "Hello" and node_id
            message = f"Hello, {self.node_id}".encode("utf-8")  # Combine and encode

            # Send to the other higher-priority instance
            for target_port in self.known_ports:
                if target_port != self.port and target_port != self.bpdu[2]:
                    self.sock.sendto(message, ("127.0.0.1", target_port))
                    print(f"Node {self.node_id} sent hello to port {target_port}")

            time.sleep(2)  # Send every 2 seconds

    def listen_2(self):
        """
        Listen for hello messages.
        """
        print(f"Node {self.node_id} listening for hello messages")
        while self.running:
            try:
                # Receive the combined message
                data, addr = self.sock.recvfrom(1024)
                message = data.decode("utf-8")  # Decode the message
                hello_message, sender_id = message.split(",")  # Split into components
                sender_id = int(sender_id)  # Convert sender_id to an integer

                print(
                    f"Node {self.node_id} ({self.port}) received '{hello_message}' from Node {sender_id} ({addr[1]})"
                )
            except ValueError:
                print(
                    f"Node {self.node_id} received malformed message: {data.decode('utf-8')}"
                )
            except Exception as e:
                print(f"Error in listen_2: {e}")

    def stop(self):
        """
        Gracefully stop the node's operations.
        """
        self.running = False
        print("Node stopping...")


# Main program execution
if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python stp.py <node_id> <weight> <port>")
        sys.exit(1)

    # Parse command-line arguments
    node_id = int(sys.argv[1])
    weight = int(sys.argv[2])
    port = int(sys.argv[3])

    # Start the STP node
    node = STPNode(node_id, weight, port)

    # Start the listening phase in a separate thread
    listen_thread = threading.Thread(target=node.listen)
    listen_thread.start()

    # Start the connection phase in a separate thread
    connect_thread = threading.Thread(target=node.connect)
    connect_thread.start()

    # Wait for the connection phase to complete
    connect_thread.join()

    # Start broadcasting in a separate thread
    broadcast_thread = threading.Thread(target=node.broadcast)
    broadcast_thread.start()

    broadcast_thread.join()

    listen_thread.join()

    print(f"\033[92mElection Result: Root is {node.bpdu}\033[0m")

    # Active Communication
    if node.bpdu[0] != node.node_id:  # Exclude the lowest-priority node
        node.set_running(True)
        listen_2_thread = threading.Thread(target=node.listen_2)
        listen_2_thread.start()

        hello_thread = threading.Thread(target=node.hello)
        hello_thread.start()
