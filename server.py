import socket
import threading
import logging
import sys
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

HOST = '127.0.0.1'
PORT = 65432
RUNNING = True
clients = []
game_state = {
    "board": [["" for _ in range(3)] for _ in range(3)],
    "next_turn": None,
    "status": "ongoing"
}
usernames = set()

def handle_arguments():
    global PORT
    global HOST
    n = len(sys.argv)
    i = 1
    while i < n:
        arg = sys.argv[i]
        if arg == "-h":
            print("Usage:")
            print("-h              Show this help message")
            print("-i Host-IP      Set the host IP address (default: 127.0.0.1)")
            print("-p Host-Port    Set the host port number (default: 65432)")
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

def send_message(conn, message_type, data):
    try:
        message = json.dumps({"type": message_type, "data": data})
        conn.sendall(message.encode('utf-8'))
    except socket.error as e:
        logging.error(f"Error sending message: {e}")

def handle_client(conn, addr):
    logging.info(f"New connection from {addr}")
    clients.append(conn)
    try:
        while True:
            message = conn.recv(1024)
            if not message:
                break
            handle_message(conn, json.loads(message.decode('utf-8')))
    except socket.error as e:
        logging.error(f"Socket error with {addr}: {e}")
    finally:
        conn.close()
        clients.remove(conn)
        logging.info(f"Connection closed with {addr}")

def handle_message(conn, message):
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

def handle_join(conn, username):
    if not username or username in usernames:
        send_message(conn, "error", {"message": "Invalid or duplicate username."})
    elif len(usernames) == 2:
        send_message(conn, "error", {"message": "Game already started between two players"})
    else:
        usernames.add(username)
        game_state["next_turn"] = game_state["next_turn"] or username
        send_message(conn, "move_ack", {"message": f"{username} joined the game."})
        logging.info(f"{username} joined the game.")

def handle_move(conn, username, position):
    # Check if username is valid
    if username not in usernames:
        send_message(conn, "error", {"message": "Username not recognized."})
        return

    # Check if position is valid
    if not position or "row" not in position or "col" not in position:
        send_message(conn, "error", {"message": "Invalid move position."})
        return
    
    row, col = position["row"], position["col"]
    if not (0 <= row < 3 and 0 <= col < 3) or game_state["board"][row][col] != "":
        send_message(conn, "error", {"message": "Invalid or occupied move position. Redo your move"})
        return
    
    # Ensure it's the player's turn
    if game_state["next_turn"] != username:
        send_message(conn, "error", {"message": "It's not your turn."})
        return

    # Assign symbol based on player turn
    symbol = "X" if username == list(usernames)[0] else "O"
    game_state["board"][row][col] = symbol

    # Switch turn to the other player
    game_state["next_turn"] = [user for user in usernames if user != username][0]

    update_all_clients()
    check_game_status()

    send_message(conn, "move_ack", {"message": f"Move accepted for {username} at position ({row}, {col})"})

    logging.info(f"{username} made a move at position ({row}, {col})")

def handle_chat(conn, username, chat_message):
    if username not in usernames or not chat_message:
        send_message(conn, "error", {"message": "Invalid chat message or unrecognized username."})
    else:
        broadcast_message("chat", {"username": username, "message": chat_message})
        logging.info(f"Broadcasting chat from {username}: {chat_message}")

def handle_quit(conn, username):
    if username in usernames:
        usernames.remove(username)
        broadcast_message("chat", {"username": "Server", "message": f"{username} has left the game."})
        logging.info(f"{username} has left the game.")

def broadcast_message(message_type, data):
    for client in clients:
        send_message(client, message_type, data)

def update_all_clients():
    broadcast_message("game_update", {
        "board": game_state["board"],
        "next_turn": game_state["next_turn"],
        "status": game_state["status"]
    })

def check_game_status():
    for i in range(3):
        if game_state["board"][i][0] == game_state["board"][i][1] == game_state["board"][i][2] != "":
            end_game(game_state["board"][i][0])
            return
        if game_state["board"][0][i] == game_state["board"][1][i] == game_state["board"][2][i] != "":
            end_game(game_state["board"][0][i])
            return
    if game_state["board"][0][0] == game_state["board"][1][1] == game_state["board"][2][2] != "":
        end_game(game_state["board"][0][0])
        return
    if game_state["board"][0][2] == game_state["board"][1][1] == game_state["board"][2][0] != "":
        end_game(game_state["board"][0][2])
        return
    if all(cell != "" for row in game_state["board"] for cell in row):
        game_state["status"] = "draw"
        broadcast_message("game_result", {"result": "draw"})
        logging.info("Game ended in a draw.")

def end_game(winner):
    game_state["status"] = "win"
    broadcast_message("game_result", {"result": "win", "winner": winner})
    logging.info(f"Game ended with winner: {winner}")

def start_server():
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
