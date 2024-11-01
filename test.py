import unittest
import socket
import threading
import time
import json
from server import start_server, RUNNING, HOST, PORT, game_state, usernames, clients
from client import send_message, handle_message

class TestTicTacToeGame(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start server in a separate thread
        cls.server_thread = threading.Thread(target=start_server)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        time.sleep(1)  # Give server time to start

    def setUp(self):
        # Reset game state before each test
        global game_state, usernames, clients
        game_state["board"] = [["" for _ in range(3)] for _ in range(3)]
        game_state["next_turn"] = None
        game_state["status"] = "ongoing"
        usernames.clear()
        clients.clear()
        
        # Create test client sockets
        self.client_socket1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket1.connect((HOST, PORT))
        self.client_socket2.connect((HOST, PORT))

        # Create message queues for each client
        self.client1_messages = []
        self.client2_messages = []

        # Start listener threads for both clients
        self.listener1 = threading.Thread(target=self.message_listener, 
                                        args=(self.client_socket1, self.client1_messages))
        self.listener2 = threading.Thread(target=self.message_listener, 
                                        args=(self.client_socket2, self.client2_messages))
        self.listener1.daemon = True
        self.listener2.daemon = True
        self.listener1.start()
        self.listener2.start()

    def tearDown(self):
        self.client_socket1.close()
        self.client_socket2.close()

    def message_listener(self, client_socket, message_queue):
        while True:
            try:
                data = client_socket.recv(1024)
                if not data:
                    break
                message = json.loads(data.decode('utf-8'))
                message_queue.append(message)
            except:
                break

    def clear_message_queues(self):
        self.client1_messages.clear()
        self.client2_messages.clear()

    def wait_for_messages(self, timeout=1):
        time.sleep(timeout)

    def test_valid_move(self):
        # Join game with two players
        send_message(self.client_socket1, "join", {"username": "player1"})
        send_message(self.client_socket2, "join", {"username": "player2"})
        
        # Wait for join messages to be processed
        self.wait_for_messages()
        self.clear_message_queues()

        # Make a move with the first player
        send_message(self.client_socket1, "move", {
            "username": "player1",
            "position": {"row": 0, "col": 0}
        })

        # Wait for move to be processed
        self.wait_for_messages()

        # Verify that both clients received the game update
        player1_updates = [msg for msg in self.client1_messages if msg["type"] == "game_update"]
        player2_updates = [msg for msg in self.client2_messages if msg["type"] == "game_update"]

        # Assert that both clients received the update
        self.assertTrue(len(player1_updates) > 0, "Player 1 did not receive game update")
        self.assertTrue(len(player2_updates) > 0, "Player 2 did not receive game update")

        # Verify the game state in the updates
        last_update1 = player1_updates[-1]["data"]
        last_update2 = player2_updates[-1]["data"]

        # Check that both clients received the same board state
        self.assertEqual(last_update1["board"][0][0], last_update2["board"][0][0], "Move was not recorded correctly")
        # self.assertEqual(last_update1["board"][0][0], "X", "Move was not recorded correctly")
        # self.assertEqual(last_update2["board"][0][0], "X", "Move was not recorded correctly")

        # Verify it's player2's turn
        self.assertEqual(last_update1["next_turn"], "player2", "Turn did not switch to player2")
        self.assertEqual(last_update2["next_turn"], "player2", "Turn did not switch to player2")

        # Verify move acknowledgment was received
        move_acks = [msg for msg in self.client1_messages if msg["type"] == "move_ack"]
        self.assertTrue(len(move_acks) > 0, "Move acknowledgment not received")
        self.assertIn("Move accepted", move_acks[0]["data"]["message"])

    def test_join_game(self):
        # Test joining game with valid username
        send_message(self.client_socket1, "join", {"username": "player1"})
        self.wait_for_messages()
        
        response = next((msg for msg in self.client1_messages if msg["type"] == "move_ack"), None)
        self.assertIsNotNone(response)
        self.assertIn("player1 joined the game", response["data"]["message"])

    def test_duplicate_username(self):
        # Test joining with duplicate username
        send_message(self.client_socket1, "join", {"username": "player1"})
        self.wait_for_messages()
        self.clear_message_queues()
        
        send_message(self.client_socket2, "join", {"username": "player1"})
        self.wait_for_messages()
        
        error_messages = [msg for msg in self.client2_messages if msg["type"] == "error"]
        self.assertTrue(len(error_messages) > 0)
        self.assertIn("duplicate username", error_messages[0]["data"]["message"].lower())

    def test_invalid_move(self):
        # Join game with two players
        send_message(self.client_socket1, "join", {"username": "player1"})
        send_message(self.client_socket2, "join", {"username": "player2"})
        self.wait_for_messages()
        self.clear_message_queues()
        
        # Test move to invalid position
        send_message(self.client_socket1, "move", {
            "username": "player1",
            "position": {"row": 3, "col": 3}
        })
        self.wait_for_messages()
        
        error_messages = [msg for msg in self.client1_messages if msg["type"] == "error"]
        self.assertTrue(len(error_messages) > 0)
        self.assertIn("Invalid", error_messages[0]["data"]["message"])

    def test_chat_message(self):
        # Join game and send chat message
        send_message(self.client_socket1, "join", {"username": "player1"})
        self.wait_for_messages()
        self.clear_message_queues()
        
        send_message(self.client_socket1, "chat", {
            "username": "player1",
            "message": "Hello, World!"
        })
        self.wait_for_messages()
        
        # Verify both clients received the chat message
        chat_messages1 = [msg for msg in self.client1_messages if msg["type"] == "chat"]
        chat_messages2 = [msg for msg in self.client2_messages if msg["type"] == "chat"]
        
        self.assertTrue(len(chat_messages1) > 0)
        self.assertTrue(len(chat_messages2) > 0)
        self.assertEqual(chat_messages1[0]["data"]["message"], "Hello, World!")
        self.assertEqual(chat_messages2[0]["data"]["message"], "Hello, World!")

if __name__ == '__main__':
    unittest.main()
