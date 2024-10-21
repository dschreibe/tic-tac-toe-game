import socket
import logging
import sys
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

HOST = None  # Server's IP address or DNS name
PORT = 65432  # Port the server is listening on

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

def send_message(client_socket, message_type, data):
    message = {
        "type": message_type,
        "data": data
    }
    client_socket.sendall(json.dumps(message).encode('utf-8'))

def handle_server_response(client_socket):
    while True:
        response = client_socket.recv(1024)
        if not response:
            logging.info("Connection closed by server.")
            return False

        message = json.loads(response.decode('utf-8'))
        handle_message(message)
        
        # Exit loop after processing message to allow for new input
        if message["type"] in ["move_ack", "error", "game_result", "chat"]:
            break
    return True


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

def connect_to_server():
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((HOST, PORT))
        logging.info(f"Connected to server at {HOST}:{PORT}")

        while True:
            message = input("Enter message type (join/move/chat/quit) or 'exit' to disconnect: ")
            if message.lower() == 'exit':
                break

            if message == "join":
                username = input("Enter your username: ")
                send_message(client_socket, "join", {"username": username})
                if not handle_server_response(client_socket):
                    break

            elif message == "move":
                username = input("Enter your username: ")
                row = int(input("Enter row (0-2): "))
                col = int(input("Enter column (0-2): "))
                send_message(client_socket, "move", {"username": username, "position": {"row": row, "col": col}})
                if not handle_server_response(client_socket):
                    break

            elif message == "chat":
                username = input("Enter your username: ")
                chat_message = input("Enter your message: ")
                send_message(client_socket, "chat", {"username": username, "message": chat_message})
                if not handle_server_response(client_socket):
                    break

            elif message == "quit":
                username = input("Enter your username: ")
                send_message(client_socket, "quit", {"username": username})
                if not handle_server_response(client_socket):
                    break
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

if __name__ == "__main__":
    handle_arguments()
    connect_to_server()
