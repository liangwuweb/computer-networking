# import socket programming library
import socket
import sys

# import thread module
from _thread import *
import threading

print_lock = threading.Lock()

def threaded(client):
    print("Thread started for a client")  # Confirm that the thread is running
    
    # Receive "want game" message from the client
    want_game = client.recv(2)
    if want_game == bytes([0, 0]):
        print("Received valid 'want game' message from client")
        # Proceed with game setup or other communication here
        print("Client verified successfully, ready for game setup")
    else:
        print("Invalid message received, disconnecting client")
        client.close()
        return  # Exit the function if verification fails

    #Keep the client connection open if additional interaction is needed
    while True:
        data = client.recv(1024)  # Expect more messages from client
        if not data:
            print("Client disconnected.")
            break
        print(f"Received message from client: {data.decode()}")


    # Connection closed
    client.close()




def Main():
	# Check if a port number is provided as an argument
  if len(sys.argv) != 2:
    print("Usage: python war-server.py <port>")
    sys.exit(1)

	# reserve a port on your computer
	# in our case it is 12345 but it
	# can be anything
  # Use the port provided by the user
  port = int(sys.argv[1])
  host = "127.0.0.1"
  s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  s.bind((host, port))
  print("socket binded to port", port)

	# put the socket into listening mode
  s.listen(2)
  print("Socket is listening for two connections")

  clients = []
  
	# a forever loop until client wants to exit
  while len(clients) < 2:

		# establish connection with client
    client, addr = s.accept()
    print('Connected to :', addr[0], ':', addr[1])

    start_new_thread(threaded, (client,))
    clients.append(client)
		
 

if __name__ == '__main__':
	Main()
