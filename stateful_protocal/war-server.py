import socket
import sys
import random
from threading import Barrier, Thread

# Initialize a Barrier for 2 clients
barrier = Barrier(2)

# Thread function to handle game setup and communication for each client
def threaded(client, cards):
    # Wait until both clients have reached this point
    barrier.wait()

    # Send "game start" command with cards
    try:
        game_start_command = bytes([1])  # Assuming "1" is the game start command
        payload = bytes(cards)           # Convert the list of cards to bytes
        client.send(game_start_command + payload)
        print(f"Sent 'game start' message with cards: {cards}")
    except Exception as e:
        print(f"Error sending data to client: {e}")
        client.close()
        return

    # Keep the client connection open if additional interaction is needed
    while True:
        try:
            data = client.recv(2)  # Expect more messages from client
            if not data:
                print("Client disconnected.")
                break
            print(f"Received message from client: {data[0]} {data[1]}")
        except Exception as e:
            print(f"Error receiving data from client: {e}")
            break

    # Connection closed
    client.close()

def Main():
    if len(sys.argv) != 2:
        print("Usage: python war-server.py <port>")
        sys.exit(1)

    # Use the port provided by the user
    port = int(sys.argv[1])
    host = "127.0.0.1"
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((host, port))
    print("Socket bound to port", port)

    # Put the socket into listening mode
    s.listen(2)
    print("Socket is listening for two connections")

    clients = []
    threads = []

    # Accept connections until two clients connect and send the "want game" message
    while len(clients) < 2:
        client, addr = s.accept()
        print('Connected to:', addr[0], ':', addr[1])

        # Receive and verify the "want game" message
        want_game = client.recv(2)
        if want_game == bytes([0, 0]):
            print("Received valid 'want game' message from client")
            clients.append(client)
        else:
            print("Invalid message received, disconnecting client")
            client.close()

    # Shuffle and deal cards once both clients have connected and been verified
    deck = list(range(52))            # Standard deck of 52 cards
    random.shuffle(deck)               # Shuffle the deck
    player1_cards = deck[:26]          # First 26 cards for player 1
    player2_cards = deck[26:]          # Last 26 cards for player 2

    # # Start a new thread for each client and send their cards after reaching the barrier
    # for i, client in enumerate(clients):
    #     thread = Thread(target=threaded, args=(client, player1_cards if i == 0 else player2_cards))
    #     thread.start()
    #     threads.append(thread)

    # # Join threads to keep the server running until both clients are finished
    # for thread in threads:
    #     thread.join()
    # Start a new thread for each client and explicitly assign their cards
    thread1 = Thread(target=threaded, args=(clients[0], player1_cards))
    thread2 = Thread(target=threaded, args=(clients[1], player2_cards))

    thread1.start()
    thread2.start()

    # Join threads to keep the server running until both clients are finished
    thread1.join()
    thread2.join()

if __name__ == '__main__':
    Main()
