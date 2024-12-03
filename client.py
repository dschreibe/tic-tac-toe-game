import socket
import logging
import sys
import json
import threading
import time
from encryption import MessageEncryption, KeyExchange
from gui_client import start_gui

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

HOST = None  # Server's IP address or DNS name
PORT = 65432  # Port the server is listening on
current_username = None  # Store the current user's username

# Initialize encryption
key_exchange = KeyExchange()
encryption = None  # Will be initialized after key exchange

# Parses command-line arguments to set the server's host and port values
def handle_arguments():
    global HOST
    global PORT
    n = len(sys.argv)
    i = 1
    use_gui = False
    port_specified = False
    while i < n:
        arg = sys.argv[i]
        if arg == "-h":
            print("Usage:")
            print("-h              Show this help message")
            print("-i Host-IP      Set the host IP address (REQUIRED)")
            print("-p Host-Port    Set the host port number (REQUIRED)")
            print("-g              Use GUI interface")
            sys.exit(0)
        elif arg == "-g":
            use_gui = True
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
                        port_specified = True
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
        else:
            print(f"Error: Unknown argument '{arg}'")
            print("Use -h for help")
            sys.exit(1)
        i += 1

    if not port_specified:
        print("Error: Port number (-p) is required")
        print("Use -h for help")
        sys.exit(1)

    if HOST is None:
        print("Error: -i (IP address) is required")
        sys.exit(1)

    return use_gui

# Sends a message to the server with a specified type and data payload
def send_message(client_socket, message_type, data):
    message = {
        "type": message_type,
        "data": data
    }
    encrypted_message = encryption.encrypt_message(json.dumps(message) + '\n')
    client_socket.sendall(encrypted_message)

# Continuously listens for responses from the server and processes each message
def handle_server_response(client_socket):
    buffer = b""
    while True:
        try:
            # Receives data from the server in chunks
            chunk = client_socket.recv(1024)
            if not chunk:
                logging.info("Connection closed by server.")
                break

            # Make sure encryption is initialized
            if encryption is None:
                logging.error("Encryption not initialized")
                break

            buffer += chunk

            try:
                # Try to decrypt the entire buffer
                decrypted_data = encryption.decrypt_message(buffer)
                buffer = b""  # Clear buffer after successful decryption
                
                # Process each complete message
                lines = decrypted_data.split('\n')
                for line in lines:
                    if line:
                        try:
                            message = json.loads(line)
                            print()
                            handle_message(message)
                        except json.JSONDecodeError as e:
                            logging.error(f"JSON decode error: {e} - Line: {line}")
            except Exception as e:
                # Placeholder
                continue

        except socket.error as e:
            logging.error(f"Socket error: {e}")
            break

# Formats the board as a 3x3 grid
def format_board(board):
    board_str = "\n"
    for row in range(3):
        board_str += f" {board[row][0] or ' '} | {board[row][1] or ' '} | {board[row][2] or ' '} \n"
        if row < 2:
            board_str += "---+---+---\n"
    return board_str

# Handles individual messages from the server based on message type
def handle_message(message):
    if message["type"] == "game_update":
        board = message["data"]["board"]
        next_turn = message["data"]["next_turn"]
        status = message["data"]["status"]
        logging.info("\nCurrent board state:")
        logging.info(format_board(board))
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
    global current_username
    
    try:
        # Creates a TCP socket and connects to the specified server
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((HOST, PORT))
        logging.info(f"Connected to server at {HOST}:{PORT}")
        
        # Receive server's public key
        server_public_key = client_socket.recv(1024)
        if not server_public_key:
            logging.error("Failed to receive server's public key")
            return
            
        # Generate our symmetric key and encrypt it with server's public key
        global encryption
        encryption = MessageEncryption()
        encrypted_symmetric_key = key_exchange.encrypt_symmetric_key(
            server_public_key,
            encryption.get_symmetric_key()
        )
        
        # Send encrypted symmetric key to server
        client_socket.sendall(encrypted_symmetric_key)
        
        # Start listening for server responses in a separate thread
        response_thread = threading.Thread(target=handle_server_response, args=(client_socket,))
        response_thread.daemon = True
        response_thread.start()

        # Main loop for user input, allowing the user to send various types of messages
        while True:
            # Wait for a short time to prevent the input prompt from appearing before the server response
            time.sleep(0.1)
            message = input("Enter message type (join/move/chat/reset/quit) or 'exit' to disconnect: ")
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

            elif message == "reset":
                if not current_username:
                    logging.error("Please join the game first.")
                    continue
                send_message(client_socket, "reset", {"username": current_username})

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
    use_gui = handle_arguments()
    if use_gui:
        start_gui(HOST, PORT)
    else:
        connect_to_server()
