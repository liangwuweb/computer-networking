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
    
    for card in cards:
        # Calculate and print the current round number
        current_round = 26 - len(cards) + 1
        print(f"Round {current_round}")

        # Get the current card and remove it from the list
        card = cards.pop(0)

        play_card = bytes([2, card])
        s.send(play_card)
        print(f"Sent card {card} to the server")

        # Receive the round result from the server
        round_result = s.recv(1024)
        result_command = round_result[0]
        result = round_result[1]

        if result_command == 3:  # Command 3 represents "play result"
            if result == 0:
                print(f"Round {current_round} result: Win")
            elif result == 1:
                print(f"Round result {current_round}: Draw")
            elif result == 2:
                print(f"Round result {current_round}: Lose")
        else:
            print("Unexpected result command received")

    # Close the connection
    s.close()

if __name__ == '__main__':
    Main()
