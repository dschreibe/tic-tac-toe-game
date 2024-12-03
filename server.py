import socket
import threading
import logging
import sys
import json
from encryption import MessageEncryption, KeyExchange
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler('server.log'),
        logging.StreamHandler()
    ]
)

# Default server settings for IP and port
HOST = '0.0.0.0'  # Listen on all network interfaces
PORT = 65432
RUNNING = True  # Control flag for server operation
clients = []  # List to keep track of connected clients
client_encryptions = {}  # Map client connections to their encryption objects

# Initialize key exchange
key_exchange = KeyExchange()

# Current game state including board status, turn info, and game status
game_state = {
    "board": [["" for _ in range(3)] for _ in range(3)],  # 3x3 game board initialized as empty
    "next_turn": None,  # Player whose turn is next
    "status": "waiting for players"  # Game status; could be 'waiting for players', 'ongoing', 'win', or 'draw'
}
usernames = set()  # Set of usernames to ensure unique players
client_usernames = {}  # Maps client connections to usernames

def handle_arguments():
    # Parses command-line arguments to set custom IP address and port number for the server.
    # Displays help if needed and validates argument values.
    global PORT
    global HOST
    n = len(sys.argv)
    i = 1
    port_specified = False
    while i < n:
        arg = sys.argv[i]
        if arg == "-h":
            print("Usage:")
            print("-h              Show this help message")
            print("-i Host-IP      Set the host IP address (default: 127.0.0.1)")
            print("-p Host-Port    Set the host port number (REQUIRED)")
            sys.exit(0)
        elif arg == "-i":
            if i + 1 < n:
                ip = sys.argv[i + 1]
                HOST = ip
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

def send_message(conn, message_type, data):
    # Sends a JSON-encoded message to the client.
    # conn: Client connection
    # message_type: Type of the message (e.g., "move_ack", "chat")
    # data: Message payload
    try:
        message = json.dumps({"type": message_type, "data": data}) + '\n'
        if conn in client_encryptions:
            encryption = client_encryptions[conn]
            encrypted_message = encryption.encrypt_message(message)
            # Add a small delay between messages to prevent message corruption
            time.sleep(0.05)
            conn.sendall(encrypted_message)
    except socket.error as e:
        logging.error(f"Error sending message: {e}")

def handle_client(conn, addr):
    # Manages a single client's connection, receiving messages and handling them.
    # conn: Client connection
    # addr: Client's address
    logging.info(f"New connection from {addr}")
    
    try:
        # First, send our public key to the client
        conn.sendall(key_exchange.get_public_key_bytes())
        
        # Receive the encrypted symmetric key from the client
        encrypted_symmetric_key = conn.recv(1024)
        if not encrypted_symmetric_key:
            return
            
        # Decrypt the symmetric key and create encryption object for this client
        symmetric_key = key_exchange.decrypt_symmetric_key(encrypted_symmetric_key)
        client_encryptions[conn] = MessageEncryption(symmetric_key)
            
        # Add client to the list after successful key exchange
        clients.append(conn)
        
        while True:
            encrypted_message = conn.recv(1024)
            if not encrypted_message:
                break
            encryption = client_encryptions[conn]
            decrypted_message = encryption.decrypt_message(encrypted_message)
            handle_message(conn, json.loads(decrypted_message))
    except socket.error as e:
        logging.error(f"Socket error with {addr}: {e}")
        handle_quit(conn, None)  # Let handle_quit handle the cleanup
    finally:
        if conn in client_usernames:
            username = client_usernames[conn]
            usernames.discard(username)
            del client_usernames[conn]
        if conn in client_encryptions:
            del client_encryptions[conn]
        conn.close()
        if conn in clients:
            clients.remove(conn)
        logging.info(f"Connection closed with {addr}")

def handle_message(conn, message):
    # Processes received messages based on message type and dispatches to specific handlers.
    # conn: Client connection
    # message: JSON-decoded message dictionary
    message_type = message.get("type")
    username = message["data"].get("username") if "data" in message else None

    if message_type == "join":
        handle_join(conn, username)
    elif message_type == "move":
        handle_move(conn, username, message["data"].get("position"))
    elif message_type == "chat":
        handle_chat(conn, username, message["data"].get("message"))
    elif message_type == "quit":
        handle_quit(conn, username)
    elif message_type == "reset":
        handle_reset(conn, username)

def handle_join(conn, username):
    # Manages new player joining the game, ensuring unique usernames and player limits.
    # conn: Client connection
    # username: Requested username for the player
    
    # Check if the game is full or the username is invalid
    if len(usernames) >= 2 and username not in usernames:
        send_message(conn, "error", {"message": "Game is full. Please wait for the next game."})
        return
    if not username:
        send_message(conn, "error", {"message": "Invalid username."})
        return

    # If this client already has a username, it's switching
    switching = conn in client_usernames
    
    # If another client is using this username, it's also switching
    if not switching and username in [name for name in client_usernames.values()]:
        switching = True

    # Add username to the set if it's new
    if username not in usernames:
        usernames.add(username)
        game_state["next_turn"] = game_state["next_turn"] or username

    # Update the client's username
    client_usernames[conn] = username

    # Send appropriate message based on whether switching or joining
    if switching:
        send_message(conn, "move_ack", {"message": f"Switched to username: {username}"})
    else:
        send_message(conn, "move_ack", {"message": f"{username} joined the game."})
    
    if len(usernames) == 2:
        game_state["status"] = "ongoing"
        broadcast_message("chat", {
            "username": "Server", 
            "message": f"Game started! {game_state['next_turn']}'s turn."
        })
    
    # update_all_clients()
    
    logging.info(f"{'Switched to' if switching else 'Joined as'} {username}")

def handle_move(conn, username, position):
    # Validates and processes player moves, updating the board and checking for game status.
    # conn: Client connection
    # username: Player's username making the move
    # position: Target position on the board for the move
    if username not in usernames:
        send_message(conn, "error", {"message": "Username not recognized."})
        return

    if len(usernames) != 2:
        send_message(conn, "error", {"message": f"Invalid number of players. Currently, there are {len(usernames)} player(s). Please wait for another player to join or use the join command."})
        return

    if not position or "row" not in position or "col" not in position:
        send_message(conn, "error", {"message": "Invalid move position."})
        return

    row, col = position["row"], position["col"]
    if not (0 <= row < 3 and 0 <= col < 3) or game_state["board"][row][col] != "":
        send_message(conn, "error", {"message": "Invalid or occupied move position. Redo your move"})
        return

    if game_state["next_turn"] != username:
        send_message(conn, "error", {"message": "It's not your turn."})
        return

    symbol = "X" if username == list(usernames)[0] else "O"
    game_state["board"][row][col] = symbol

    game_state["next_turn"] = [user for user in usernames if user != username][0]

    update_all_clients()
    check_game_status()

    send_message(conn, "move_ack", {"message": f"Move accepted for {username} at position ({row}, {col})"})

    logging.info(f"{username} made a move at position ({row}, {col})")

def handle_chat(conn, username, chat_message):
    # Broadcasts chat messages to all connected players.
    # conn: Client connection
    # username: Player's username
    # chat_message: Chat message text
    if username not in usernames or not chat_message:
        send_message(conn, "error", {"message": "Invalid chat message or unrecognized username."})
    else:
        broadcast_message("chat", {"username": username, "message": chat_message})
        logging.info(f"Broadcasting chat from {username}: {chat_message}")

def handle_quit(conn, username):
    # Handles player quitting, updating game state and notifying other players.
    # conn: Client connection
    # username: Player's username
    if username in usernames:
        usernames.remove(username)
        broadcast_message("chat", {"username": "Server", "message": f"{username} has left the game."})
    if conn in client_usernames:
        username = client_usernames[conn]
        del client_usernames[conn]
        broadcast_message("chat", {"username": "Server", "message": f"{username} has left the game. From the machine: {conn.getpeername()}" })
        logging.info(f"{username} has left the game.")
        # reset_game() # Maybe don't reset game when someone leaves

def handle_reset(conn, username):
    # Handles game reset requests from clients
    # conn: Client connection
    # username: Player's username
    if username not in usernames:
        send_message(conn, "error", {"message": "You must join the game first."})
        return
        
    reset_game()
    broadcast_message("chat", {
        "username": "Server",
        "message": f"{username} has reset the game! Please rejoin with usernames to start a new game."
    })

def broadcast_message(message_type, data):
    # Sends a message to all connected clients.
    # message_type: Type of the message
    # data: Message content
    for client in clients:
        send_message(client, message_type, data)

def update_all_clients():
    # Sends the updated game state to all players after each move.
    broadcast_message("game_update", {
        "board": game_state["board"],
        "next_turn": game_state["next_turn"],
        "status": game_state["status"]
    })

def reset_game():
    # Resets the game board and clears players' data for a new game session.
    game_state["board"] = [["" for _ in range(3)] for _ in range(3)]
    game_state["next_turn"] = None
    game_state["status"] = "waiting for players"
    client_usernames.clear()
    usernames.clear()
    logging.info("Game reset")

def check_game_status():
    # Checks for a win, draw, or ongoing game status after each move.
    for i in range(3):
        if game_state["board"][i][0] == game_state["board"][i][1] == game_state["board"][i][2] != "":
            end_game(game_state["board"][i][0])
            return

    # Check columns
    for i in range(3):
        if game_state["board"][0][i] == game_state["board"][1][i] == game_state["board"][2][i] != "":
            end_game(game_state["board"][0][i])
            return

    # Check diagonals
    if game_state["board"][0][0] == game_state["board"][1][1] == game_state["board"][2][2] != "":
        end_game(game_state["board"][0][0])
        return

    if game_state["board"][0][2] == game_state["board"][1][1] == game_state["board"][2][0] != "":
        end_game(game_state["board"][0][2])
        return

    # Check for draw
    if all(cell != "" for row in game_state["board"] for cell in row):
        broadcast_message("game_result", {"result": "draw"})
        logging.info("Game ended in a draw.")
        reset_game()

def end_game(winner_symbol):
    # Ends the game and announces the winner, if there is one.
    # winner_symbol: Symbol ('X' or 'O') of the winning player
    winner_username = list(usernames)[0] if winner_symbol == "X" else list(usernames)[1]
    broadcast_message("game_result", {
        "result": "win",
        "winner": winner_username,
        "symbol": winner_symbol
    })
    logging.info(f"Game ended. Winner: {winner_username} ({winner_symbol})")
    reset_game()

def start_server():
    # Starts the server, accepting and managing client connections in threads.
    global RUNNING
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    server_socket.settimeout(1)
    logging.info(f"Server started, listening on {HOST}:{PORT}")

    try:
        while RUNNING:
            try:
                conn, addr = server_socket.accept()
                threading.Thread(target=handle_client, args=(conn, addr)).start()
            except socket.timeout:
                continue
    except KeyboardInterrupt:
        logging.info("Server shutting down.")
        RUNNING = False
    finally:
        server_socket.close()

if __name__ == "__main__":
    handle_arguments()
    start_server()
