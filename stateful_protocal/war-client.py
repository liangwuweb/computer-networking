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

    #round_num = 1
    
    # while True:
    #     # Send message to the server
    #     s.send(message.encode('ascii'))

    #     # Receive message from the server
    #     data = s.recv(1024)

    #     # Print the received message (would be reversed message from server)
    #     print('Received from the server:', str(data.decode('ascii')))
        
    #     # Increment the round number
    #     round_num += 1

    #     # Break the loop after 26 rounds
    #     if round_num == 26:
    #         break

    # Close the connection
    s.close()

if __name__ == '__main__':
    Main()
