import tkinter as tk
from tkinter import messagebox, simpledialog
import socket
import threading
import json
import logging
from encryption import MessageEncryption, KeyExchange

class TicTacToeGUI:
    def __init__(self, host, port):
        self.root = tk.Tk()
        self.root.title("Tic Tac Toe")
        self.host = host
        self.port = port
        self.socket = None
        self.encryption = None
        self.username = None
        self.connected = False
        self.game_over = False
        
        # Game state
        self.board = [['' for _ in range(3)] for _ in range(3)]
        self.buttons = [[None for _ in range(3)] for _ in range(3)]
        
        # Create GUI elements
        self.create_gui()
        
        # Connect to server
        self.connect_to_server()
        
        # Start message receiving thread
        self.receive_thread = threading.Thread(target=self.receive_messages)
        self.receive_thread.daemon = True
        self.receive_thread.start()

    def create_gui(self):
        # Status label
        self.status_label = tk.Label(self.root, text="Connecting to server...", font=('Arial', 12))
        self.status_label.pack(pady=10)
        
        # Game board
        board_frame = tk.Frame(self.root)
        board_frame.pack()
        
        for i in range(3):
            for j in range(3):
                self.buttons[i][j] = tk.Button(
                    board_frame,
                    text='',
                    font=('Arial', 20),
                    width=5,
                    height=2,
                    command=lambda row=i, col=j: self.make_move(row, col)
                )
                self.buttons[i][j].grid(row=i, column=j)
        
        # Chat frame
        chat_frame = tk.Frame(self.root)
        chat_frame.pack(pady=10)
        
        self.chat_text = tk.Text(chat_frame, height=5, width=40)
        self.chat_text.pack()
        
        chat_input_frame = tk.Frame(chat_frame)
        chat_input_frame.pack(fill=tk.X)
        
        self.chat_entry = tk.Entry(chat_input_frame)
        self.chat_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        send_button = tk.Button(chat_input_frame, text="Send", command=self.send_chat)
        send_button.pack(side=tk.RIGHT)
        
        # Button frame for Reset and Change Username
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=5)
        
        # Reset button
        reset_button = tk.Button(button_frame, text="Reset Game", command=self.reset_game)
        reset_button.pack(side=tk.LEFT, padx=5)
        
        # Change Username button
        change_username_button = tk.Button(button_frame, text="Change Username", command=self.change_username)
        change_username_button.pack(side=tk.LEFT, padx=5)

    def connect_to_server(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            
            # Handle key exchange
            key_exchange = KeyExchange()
            server_public_key = self.socket.recv(1024)
            
            # Create encryption object
            self.encryption = MessageEncryption()
            
            # Encrypt our symmetric key with server's public key
            encrypted_symmetric_key = key_exchange.encrypt_symmetric_key(
                server_public_key,
                self.encryption.get_symmetric_key()
            )
            
            # Send our encrypted symmetric key
            self.socket.sendall(encrypted_symmetric_key)
            
            # Start message receiving thread
            self.receive_thread = threading.Thread(target=self.receive_messages)
            self.receive_thread.daemon = True
            self.receive_thread.start()
            
            # Get username and join game
            self.username = simpledialog.askstring("Username", "Enter your username:")
            if not self.username:
                self.root.quit()
                return
            
            # Send join message
            self.connected = True
            self.send_message("join", {"username": self.username})
            
            # Update status
            self.status_label.config(text=f"Connected to {self.host}:{self.port} as {self.username}")
            logging.info(f"Connected to server at {self.host}:{self.port} as {self.username}")
            
        except Exception as e:
            logging.error(f"Connection Error: {str(e)}")
            self.root.quit()

    def receive_messages(self):
        buffer = b""
        while True:
            try:
                data = self.socket.recv(4096)
                if not data:
                    logging.error("Server connection lost")
                    self.root.quit()
                    break

                buffer += data
                
                try:
                    # Try to decrypt the entire buffer
                    decrypted_data = self.encryption.decrypt_message(buffer)
                    buffer = b""  # Clear buffer after successful decryption
                    
                    # Process each complete message
                    lines = decrypted_data.split('\n')
                    for line in lines:
                        if line:
                            try:
                                message = json.loads(line)
                                self.handle_message(message)
                            except json.JSONDecodeError as e:
                                logging.error(f"JSON decode error: {e} - Line: {line}")
                except Exception as e:
                    # If decryption fails, keep the data in buffer
                    continue

            except Exception as e:
                logging.error(f"Error receiving message: {e}")
                break

        self.socket.close()
        self.root.quit()

    def display_system_message(self, message):
        self.chat_text.insert(tk.END, f"System: {message}\n")
        self.chat_text.see(tk.END)

    def handle_message(self, message):
        message_type = message["type"]
        data = message["data"]
        
        if message_type == "game_update":
            self.board = data["board"]
            next_turn = data.get("next_turn")
            status = data.get("status")
            
            # Update the GUI board
            for i in range(3):
                for j in range(3):
                    self.buttons[i][j].config(text=self.board[i][j] if self.board[i][j] else '')
            
            # Display game status in chat
            if status == "waiting for players":
                self.display_system_message("Waiting for another player to join...")
            elif status == "ongoing":
                if next_turn == self.username:
                    self.display_system_message("It's your turn!")
                else:
                    self.display_system_message(f"Waiting for {next_turn}'s move...")

        elif message_type == "game_result":
            result = data["result"]
            self.game_over = True
            if result == "win":
                self.status_label.config(text=f"Game Over - Winner: {data['winner']}")
                self.display_system_message(f"Game Over - {data['winner']} wins!")
            elif result == "draw":
                self.status_label.config(text="Game Over - Draw!")
                self.display_system_message("Game Over - It's a draw!")

        elif message_type == "move_ack":
            logging.info(f"Move acknowledged: {data['message']}")
            self.display_system_message(data['message'])

        elif message_type == "join":
            self.display_system_message(data['message'])

        elif message_type == "error":
            logging.error(f"Error: {data['message']}")
            self.display_system_message(f"Error: {data['message']}")

        elif message_type == "chat":
            username = data["username"]
            chat_message = data["message"]
            self.chat_text.insert(tk.END, f"{username}: {chat_message}\n")
            self.chat_text.see(tk.END)

    def make_move(self, row, col):
        if not self.connected:
            return
        if self.game_over:
            self.display_system_message("Game is over. Click Reset to start a new game!")
            return
        logging.info(f"Making move: {row}, {col}")
        self.send_message("move", {"username": self.username, "position": {"row": row, "col": col}})

    def send_chat(self):
        if not self.connected:
            return
        if self.game_over:
            self.display_system_message("Game is over. Click Reset to start a new game!")
            return
        message = self.chat_entry.get().strip()
        if message:
            self.send_message("chat", {"username": self.username, "message": message})
            self.chat_entry.delete(0, tk.END)

    def clear_board(self):
        self.board = [['' for _ in range(3)] for _ in range(3)]
        for i in range(3):
            for j in range(3):
                self.buttons[i][j].config(text='')
        self.status_label.config(text="Connecting to server...")
        self.chat_text.delete(1.0, tk.END)

    def reset_game(self):
        if not self.connected:
            return
        if self.game_over:
            self.clear_board()
            self.game_over = False
            # Get new username
            new_username = simpledialog.askstring("Username", "Enter your username:")
            if new_username:
                self.username = new_username
                self.send_message("join", {"username": self.username})
                self.display_system_message(f"Rejoining as: {self.username}")
                self.status_label.config(text=f"Connected to {self.host}:{self.port} as {self.username}")
            else:
                self.root.quit()
                return
        else:
            self.send_message("reset", {"username": self.username})

    def change_username(self):
        if not self.connected:
            return
        new_username = simpledialog.askstring("Username", "Enter new username:")
        if new_username:
            old_username = self.username
            self.username = new_username
            self.send_message("join", {"username": self.username})
            self.display_system_message(f"Changing username from {old_username} to {self.username}")
            self.status_label.config(text=f"Connected to {self.host}:{self.port} as {self.username}")

    def send_message(self, message_type, data):
        if not self.connected:
            logging.error("Not connected to server")
            return
        if self.game_over and message_type not in ["join", "reset"]:
            logging.info("Game is over. Click Reset to start a new game!")
            return
        try:
            message = json.dumps({"type": message_type, "data": data}) + '\n'
            encrypted_message = self.encryption.encrypt_message(message)
            self.socket.sendall(encrypted_message)
        except Exception as e:
            logging.error(f"Error sending message: {e}")

    def run(self):
        self.root.mainloop()
        if self.socket:
            if self.username:
                self.send_message("quit", {"username": self.username})
            self.socket.close()

def start_gui(host, port):
    gui = TicTacToeGUI(host, port)
    gui.run()
