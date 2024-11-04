import socket
import sys
import random
from threading import Barrier, Thread, Condition

# Initialize a Barrier and Condition
barrier = Barrier(2)
condition = Condition()

# Shared dictionary to store cards received from each client
round_cards = {}


def thr_join():
    condition.acquire()
    while len(round_cards) < 2:
      condition.wait()
    condition.release()

def compare_and_send_results(client1, client2):
    # Extract the cards
    card1 = round_cards[0]
    card2 = round_cards[1]

    rank1=card1 % 13 + 2
    rank2=card2 % 13 + 2
    
    # Compare cards and determine results
    if rank1 > rank2:
        result_client1, result_client2 = 0, 2  # Client 1 wins, Client 2 loses
    elif rank1 < rank2:
        result_client1, result_client2 = 2, 0  # Client 1 loses, Client 2 wins
    else:
        result_client1, result_client2 = 1, 1  # Draw for both clients

    # Send results to both clients
    client1.send(bytes([3, result_client1]))
    client2.send(bytes([3, result_client2]))
    
    print(f"Sent result to client 1: {'Win' if result_client1 == 0 else 'Draw' if result_client1 == 1 else 'Lose'}")
    print(f"Sent result to client 2: {'Win' if result_client2 == 0 else 'Draw' if result_client2 == 1 else 'Lose'}")

    # Clear round_cards for the next round
    round_cards.clear()

# Thread function to handle game setup and communication for each client
def threaded(client, client_id, cards):
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
            command = data[0]
            card_played = data[1]
            print(f"Client {client_id+1} played card: {card_played}")
        except Exception as e:
            print(f"Error receiving data from client: {e}")
            break
        
        if command == 2:
            condition.acquire()
            round_cards[client_id] = card_played
            if len(round_cards) >= 2:
                condition.notify()
            condition.release()

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

    # Start a new thread for each client and explicitly assign their cards
    thread1 = Thread(target=threaded, args=(clients[0], 0, player1_cards))
    thread2 = Thread(target=threaded, args=(clients[1], 1, player2_cards))

    thread1.start()
    thread2.start()

    # Main loop for managing rounds
    for i in range(26):
      print(f"Round {i+1} start")
      thr_join()  # Wait for both cards to be played
      compare_and_send_results(clients[0], clients[1])
      print(f"Round {i+1} end\r\n")

    # Join threads to keep the server running until both clients are finished
    thread1.join()
    thread2.join()

    # Close the server socket
    s.close()
    print("Server socket closed. Game over.")

if __name__ == '__main__':
    Main()
