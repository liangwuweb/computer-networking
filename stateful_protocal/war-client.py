import socket
import sys

def Main():
    if len(sys.argv) != 3:
        print("Usage: python war-client.py <host> <port>")
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2])

    # Create a TCP socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Connect to the server on the local computer
    s.connect((host, port))

    # Send the "want game" message (command = 0, payload = 0)
    want_game_msg = bytes([0, 0])
    s.send(want_game_msg)
    print("Sent 'want game' message to server")

    # Receive the "game start" message from the server
    game_start_packet = s.recv(1024)

    # The first byte is the command, and the rest is the card payload
    command = game_start_packet[0]
    if command == 1:  # Check if this is the "game start" command
        cards = list(game_start_packet[1:])  # Extract the card payload
        print("Received 'game start' message with cards:", cards)
    else:
        print("Unexpected command received from server")

    # Close the connection
    s.close()

if __name__ == '__main__':
    Main()
