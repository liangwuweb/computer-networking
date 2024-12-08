import sys
import socket
import struct
import threading
import time


known_ports = [5001, 5002, 5003]


class STPNode:
    def __init__(self, node_id, weight, port):
        self.node_id = node_id
        self.weight = weight
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", self.port))
        self.received_messages = set()  # Track received (message, sender) tuples
        self.running = True  # Control flag for threads
        print(f"Node {self.node_id} initialized on port {self.port}")

    def broadcast(self):
        """
        Periodically broadcast this node's ID and weight to all other nodes.
        """
        message = self.weight + self.node_id
        packed_data = struct.pack("!I", message)
        while self.running:
            for target_port in known_ports:
                if target_port != self.port:
                    self.sock.sendto(packed_data, ("127.0.0.1", target_port))
                    print(f"Broadcasted to port {target_port}: {packed_data}")
            time.sleep(1)  # Broadcast every 1 seconds

    def listen(self):
        """
        Listen for incoming messages from other nodes.
        """
        print(f"Node {self.node_id} listening on port {self.port}")
        try:
            while self.running:
                if len(self.received_messages) >= 2:
                    # send acknowledgement to other two nodes
                # if node receives two ack, then it stop boardcasting
                data, addr = self.sock.recvfrom(1024)  # Buffer size is 1024 bytes
                received_message = struct.unpack("!I", data)[0]
                message_with_sender = (received_message, addr)

                # Check if the message+sender tuple is new
                if message_with_sender not in self.received_messages:
                    self.received_messages.add(message_with_sender)
                    print(f"Received {received_message} from {addr}, adding to set.")
                else:
                    print(
                        f"Duplicate message {received_message} from {addr}, ignoring."
                    )
        except KeyboardInterrupt:
            print("\nStopping node...")
        finally:
            self.sock.close()
            print("Socket closed.")

    def stop(self):
        """
        Stop broadcasting and listening.
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

    # Start the broadcasting thread
    broadcaster_thread = threading.Thread(target=node.broadcast, daemon=True)
    broadcaster_thread.start()

    node.listen()
