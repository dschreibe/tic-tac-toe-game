import socket
import logging
import sys
import json
import threading
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

HOST = None  # Server's IP address or DNS name
PORT = 65432  # Port the server is listening on
current_username = None  # Store the current user's username

# Parses command-line arguments to set the server's host and port values
def handle_arguments():
    global HOST
    global PORT
    n = len(sys.argv)
    i = 1
    while i < n:
        arg = sys.argv[i]
        if arg == "-h":
            print("Usage:")
            print("-h              Show this help message")
            print("-i Host-IP      Set the host IP address (required)")
            print("-p Host-Port    Set the host port number (default: 65432)")
            print("-n DNS-Name     Set the DNS name of the server")
            sys.exit(0)
        elif arg == "-i":
            if i + 1 < n:
                HOST = sys.argv[i + 1]
                i += 1
            else:
                print("Error: -i requires an IP address")
                sys.exit(1)
        elif arg == "-p":
            if i + 1 < n:
                try:
                    port = int(sys.argv[i + 1])
                    if 1 <= port <= 65535:
                        PORT = port
                    else:
                        print("Error: Port number must be between 1 and 65535")
                        sys.exit(1)
                except ValueError:
                    print("Error: Port must be an integer")
                    sys.exit(1)
                i += 1
            else:
                print("Error: -p requires a port number")
                sys.exit(1)
        elif arg == "-n":
            if i + 1 < n:
                HOST = sys.argv[i + 1]
                i += 1
            else:
                print("Error: -n requires a DNS name")
                sys.exit(1)
        else:
            print(f"Error: Unknown argument '{arg}'")
            print("Use -h for help")
            sys.exit(1)
        i += 1

    if HOST is None:
        print("Error: -i (IP address) is required")
        sys.exit(1)

# Sends a message to the server with a specified type and data payload
def send_message(client_socket, message_type, data):
    message = {
        "type": message_type,
        "data": data
    }
    client_socket.sendall((json.dumps(message) + '\n').encode('utf-8'))

# Continuously listens for responses from the server and processes each message
def handle_server_response(client_socket):
    buffer = ""
    while True:
        try:
            # Receives data from the server in chunks
            response = client_socket.recv(1024)
            if not response:
                logging.info("Connection closed by server.")
                break

            buffer += response.decode('utf-8')

            # Processes each complete line in the buffer as a separate message
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                if line:
                    try:
                        message = json.loads(line)
                        print()
                        handle_message(message)
                    except json.JSONDecodeError as e:
                        logging.error(f"JSON decode error: {e} - Line: {line}")

        except socket.error as e:
            logging.error(f"Socket error: {e}")
            break

# Handles individual messages from the server based on message type
def handle_message(message):
    if message["type"] == "game_update":
        board = message["data"]["board"]
        next_turn = message["data"]["next_turn"]
        status = message["data"]["status"]
        logging.info(f"Board: {board}")
        logging.info(f"Next turn: {next_turn}")
        logging.info(f"Game status: {status}")

    elif message["type"] == "move_ack":
        logging.info(message["data"]["message"])

    elif message["type"] == "error":
        logging.error(message["data"]["message"])

    elif message["type"] == "game_result":
        logging.info(f"Game result: {message['data']['result']}")
        if message['data']['result'] == "win":
            logging.info(f"Winner: {message['data']['winner']}")

    elif message["type"] == "chat":
        username = message["data"]["username"]
        chat_message = message["data"]["message"]
        logging.info(f"{username}: {chat_message}")

# Connects to the server, manages message sending, and listens for commands from the user
def connect_to_server():
    try:
        # Creates a TCP socket and connects to the specified server
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((HOST, PORT))
        logging.info(f"Connected to server at {HOST}:{PORT}")

        # Starts a new thread to handle responses from the server
        listener_thread = threading.Thread(target=handle_server_response, args=(client_socket,))
        listener_thread.daemon = True
        listener_thread.start()

        # Main loop for user input, allowing the user to send various types of messages
        while True:
            # Wait for a short time to prevent the input prompt from appearing before the server response
            time.sleep(0.1)
            message = input("Enter message type (join/move/chat/quit) or 'exit' to disconnect: ")
            if message.lower() == 'exit':
                break

            if message == "join":
                username = input("Enter your username: ")
                global current_username
                current_username = username
                send_message(client_socket, "join", {"username": username})

            elif message == "move":
                if not current_username:
                    logging.error("Please join the game first.")
                    continue
                try:
                    row = int(input("Enter row (0-2): "))
                    col = int(input("Enter column (0-2): "))
                except ValueError:
                    logging.error("Row and Column must be integers between 0 and 2.")
                    continue
                if not (0 <= row <= 2 and 0 <= col <= 2):
                    logging.error("Row and Column must be between 0 and 2.")
                    continue
                send_message(client_socket, "move", {"username": current_username, "position": {"row": row, "col": col}})

            elif message == "chat":
                if not current_username:
                    logging.error("Please join the game first.")
                    continue
                chat_message = input("Enter your message: ")
                send_message(client_socket, "chat", {"username": current_username, "message": chat_message})

            elif message == "quit":
                if current_username:
                    send_message(client_socket, "quit", {"username": current_username})
                break

            else:
                logging.error("Unknown message type. Please enter a valid command.")

    except ConnectionRefusedError:
        logging.error("Connection failed. Server may be unavailable.")
    except socket.error as e:
        logging.error(f"Socket error: {e}")
    finally:
        client_socket.close()
        logging.info("Disconnected from server.")

# Main entry point for the script: processes command-line arguments and connects to the server
if __name__ == "__main__":
    handle_arguments()
    connect_to_server()
