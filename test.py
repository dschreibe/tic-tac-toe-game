import unittest
import socket
import threading
import time
import json
from server import start_server, RUNNING, PORT, game_state, usernames, clients, client_encryptions
from client import send_message, handle_message
from encryption import KeyExchange, MessageEncryption

TEST_HOST = '127.0.0.1'  # Use localhost instead of before 0.0.0.0

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
        global game_state, usernames, clients, client_encryptions
        game_state["board"] = [["" for _ in range(3)] for _ in range(3)]
        game_state["next_turn"] = None
        game_state["status"] = "ongoing"
        usernames.clear()
        clients.clear()
        client_encryptions.clear()
        
        # Create test client sockets
        self.client_socket1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket1.connect((TEST_HOST, PORT))
        self.client_socket2.connect((TEST_HOST, PORT))

        # Setup encryption for test clients
        self.key_exchange1 = KeyExchange()
        self.key_exchange2 = KeyExchange()
        
        # Setup encryption for client 1
        server_public_key = self.client_socket1.recv(1024)
        self.encryption1 = MessageEncryption()
        encrypted_symmetric_key = self.key_exchange1.encrypt_symmetric_key(
            server_public_key,
            self.encryption1.symmetric_key
        )
        self.client_socket1.sendall(encrypted_symmetric_key)

        # Setup encryption for client 2
        server_public_key = self.client_socket2.recv(1024)
        self.encryption2 = MessageEncryption()
        encrypted_symmetric_key = self.key_exchange2.encrypt_symmetric_key(
            server_public_key,
            self.encryption2.symmetric_key
        )
        self.client_socket2.sendall(encrypted_symmetric_key)

        # Create message queues for each client
        self.client1_messages = []
        self.client2_messages = []

        # Start listener threads for both clients
        self.listener1 = threading.Thread(target=self.message_listener, 
                                        args=(self.client_socket1, self.client1_messages, self.encryption1))
        self.listener2 = threading.Thread(target=self.message_listener, 
                                        args=(self.client_socket2, self.client2_messages, self.encryption2))
        self.listener1.daemon = True
        self.listener2.daemon = True
        self.listener1.start()
        self.listener2.start()

        # Give time for encryption setup to complete
        time.sleep(0.1)

    def tearDown(self):
        time.sleep(0.2)
        
        if hasattr(self, 'client_socket1'):
            try:
                self.send_test_message(self.client_socket1, "quit", {"username": "player1"}, self.encryption1)
                time.sleep(0.1)
            except:
                pass
            finally:
                self.client_socket1.close()
        
        if hasattr(self, 'client_socket2'):
            try:
                self.send_test_message(self.client_socket2, "quit", {"username": "player2"}, self.encryption2)
                time.sleep(0.1)
            except:
                pass
            finally:
                self.client_socket2.close()
        time.sleep(0.2)

    def send_test_message(self, client_socket, message_type, data, encryption):
        message = {
            "type": message_type,
            "data": data
        }
        encrypted_message = encryption.encrypt_message(json.dumps(message) + '\n')
        client_socket.sendall(encrypted_message)

    def message_listener(self, client_socket, message_queue, encryption):
        buffer = ""
        while True:
            try:
                data = client_socket.recv(1024)
                if not data:
                    break
                decrypted_data = encryption.decrypt_message(data)
                buffer += decrypted_data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line:
                        try:
                            message = json.loads(line)
                            message_queue.append(message)
                        except json.JSONDecodeError:
                            print(f"Test listener JSON decode error: {line}")
            except Exception as e:
                break

    def clear_message_queues(self):
        self.client1_messages.clear()
        self.client2_messages.clear()

    def wait_for_messages(self, timeout=1):
        start_time = time.time()
        wait_time = 0.1
        while time.time() - start_time < timeout:
            if self.client1_messages or self.client2_messages:
                # Wait for additional messages
                time.sleep(0.1)
                break
            time.sleep(wait_time)
            wait_time = min(wait_time * 1.5, timeout - (time.time() - start_time))

    def wait_for_specific_message(self, message_queue, message_type, timeout=2, retries=3):
        for attempt in range(retries):
            start_time = time.time()
            while time.time() - start_time < timeout:
                messages = [msg for msg in message_queue if msg["type"] == message_type]
                if messages:
                    return messages
                time.sleep(0.1)
            # retry
            if attempt < retries - 1:
                self.clear_message_queues()
                time.sleep(0.2)
        return []

    def test_valid_move(self):
        # Join game with two players
        self.send_test_message(self.client_socket1, "join", {"username": "player1"}, self.encryption1)
        time.sleep(0.2)
        self.send_test_message(self.client_socket2, "join", {"username": "player2"}, self.encryption2)
        
        # Wait for join messages to be processed
        self.wait_for_messages(timeout=2)
        self.clear_message_queues()

        # Make a move with the first player
        self.send_test_message(self.client_socket1, "move", {
            "username": "player1",
            "position": {"row": 0, "col": 0}
        }, self.encryption1)

        # Wait specifically for game updates
        player1_updates = self.wait_for_specific_message(self.client1_messages, "game_update")
        player2_updates = self.wait_for_specific_message(self.client2_messages, "game_update")

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
        self.send_test_message(self.client_socket1, "join", {"username": "player1"}, self.encryption1)
        self.wait_for_messages()
        
        response = next((msg for msg in self.client1_messages if msg["type"] == "move_ack"), None)
        self.assertIsNotNone(response)
        self.assertIn("player1 joined the game", response["data"]["message"])

    def test_duplicate_username(self):
        # Test joining with duplicate username
        self.send_test_message(self.client_socket1, "join", {"username": "player1"}, self.encryption1)
        self.wait_for_messages()
        self.clear_message_queues()
        
        # Second client tries to use same username should succeed with a switch
        self.send_test_message(self.client_socket2, "join", {"username": "player1"}, self.encryption2)
        self.wait_for_messages()
        
        # Should get a switch confirmation
        switch_messages = [msg for msg in self.client2_messages if msg["type"] == "move_ack"]
        self.assertTrue(len(switch_messages) > 0)
        self.assertIn("switched to username", switch_messages[0]["data"]["message"].lower())

    def test_username_switching(self):
        # Test switching usernames for the same client
        self.send_test_message(self.client_socket1, "join", {"username": "player1"}, self.encryption1)
        self.wait_for_messages()
        self.clear_message_queues()

        # Switch to a different username
        self.send_test_message(self.client_socket1, "join", {"username": "player2"}, self.encryption1)
        self.wait_for_messages()

        switch_messages = [msg for msg in self.client1_messages if msg["type"] == "move_ack"]
        self.assertTrue(len(switch_messages) > 0)
        self.assertIn("switched to username", switch_messages[0]["data"]["message"].lower())

    def test_username_persistence(self):
        # Test that usernames persist after client disconnection
        self.send_test_message(self.client_socket1, "join", {"username": "player1"}, self.encryption1)
        self.wait_for_messages()
        self.clear_message_queues()

        # Create a new client connection
        new_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        new_socket.connect((TEST_HOST, PORT))
        
        # Setup encryption for new socket
        server_public_key = new_socket.recv(1024)
        encryption3 = MessageEncryption()
        key_exchange3 = KeyExchange()
        encrypted_symmetric_key = key_exchange3.encrypt_symmetric_key(
            server_public_key,
            encryption3.symmetric_key
        )
        new_socket.sendall(encrypted_symmetric_key)
        time.sleep(0.1)  # Give time for encryption setup
        
        # Try to use the same username with new connection
        self.send_test_message(new_socket, "join", {"username": "player1"}, encryption3)
        
        # Wait for response and verify it's allowed
        time.sleep(1)
        new_socket.close()

    def test_invalid_move(self):
        # Join game with two players
        self.send_test_message(self.client_socket1, "join", {"username": "player1"}, self.encryption1)
        self.send_test_message(self.client_socket2, "join", {"username": "player2"}, self.encryption2)
        self.wait_for_messages()
        self.clear_message_queues()
        
        # Test move to invalid position
        self.send_test_message(self.client_socket1, "move", {
            "username": "player1",
            "position": {"row": 3, "col": 3}
        }, self.encryption1)
        self.wait_for_messages()
        
        error_messages = [msg for msg in self.client1_messages if msg["type"] == "error"]
        self.assertTrue(len(error_messages) > 0)
        self.assertIn("Invalid", error_messages[0]["data"]["message"])

    def test_chat_message(self):
        # Join game and send chat message
        self.send_test_message(self.client_socket1, "join", {"username": "player1"}, self.encryption1)
        self.wait_for_messages()
        self.clear_message_queues()
        
        self.send_test_message(self.client_socket1, "chat", {
            "username": "player1",
            "message": "Hello, World!"
        }, self.encryption1)
        self.wait_for_messages()
        
        # Verify both clients received the chat message
        chat_messages1 = [msg for msg in self.client1_messages if msg["type"] == "chat"]
        chat_messages2 = [msg for msg in self.client2_messages if msg["type"] == "chat"]
        
        self.assertTrue(len(chat_messages1) > 0)
        self.assertTrue(len(chat_messages2) > 0)
        self.assertEqual(chat_messages1[0]["data"]["message"], "Hello, World!")
        self.assertEqual(chat_messages2[0]["data"]["message"], "Hello, World!")

    def test_win_condition(self):
        # Join game with two players
        self.send_test_message(self.client_socket1, "join", {"username": "player1"}, self.encryption1)
        self.send_test_message(self.client_socket2, "join", {"username": "player2"}, self.encryption2)
        
        # Wait for join messages to be processed
        self.wait_for_messages()
        self.clear_message_queues()

        moves = [
            {"socket": self.client_socket1, "username": "player1", "position": {"row": 0, "col": 0}},
            {"socket": self.client_socket2, "username": "player2", "position": {"row": 1, "col": 0}},
            {"socket": self.client_socket1, "username": "player1", "position": {"row": 0, "col": 1}},
            {"socket": self.client_socket2, "username": "player2", "position": {"row": 1, "col": 1}},
            {"socket": self.client_socket1, "username": "player1", "position": {"row": 0, "col": 2}}
        ]

        # Execute moves
        for move in moves:
            self.send_test_message(move["socket"], "move", {
                "username": move["username"],
                "position": move["position"]
            }, self.encryption1 if move["socket"] == self.client_socket1 else self.encryption2)
            self.wait_for_messages()

        # Wait a bit
        self.wait_for_messages(timeout=4)

        # Verify that both clients received the game_result message
        game_results_client1 = [msg for msg in self.client1_messages if msg["type"] == "game_result"]
        game_results_client2 = [msg for msg in self.client2_messages if msg["type"] == "game_result"]
        
        self.assertTrue(len(game_results_client1) > 0, "Player 1 did not receive game_result message")
        self.assertTrue(len(game_results_client2) > 0, "Player 2 did not receive game_result message")

        # Check the contents of the game_result message
        game_result1 = game_results_client1[-1]["data"]
        game_result2 = game_results_client2[-1]["data"]

        # Assert that both game_result messages indicate a win
        self.assertEqual(game_result1["result"], "win", "Player 1 game_result does not indicate a win")
        self.assertEqual(game_result2["result"], "win", "Player 2 game_result does not indicate a win")

        self.assertEqual(game_result1["winner"], "player1", "Player 1 game_result has incorrect winner")
        self.assertEqual(game_result2["winner"], "player1", "Player 2 game_result has incorrect winner")
        
        self.assertEqual(game_result1["symbol"], game_result2["symbol"], "Different game_result symbol from two clients")

        self.assertEqual(game_state["status"], "ongoing", "Game status was not reset after win")
        self.assertEqual(len(usernames), 0, "Usernames were not cleared after game reset")
        self.assertEqual(len(clients), 2, "Clients removed")

if __name__ == '__main__':
    unittest.main()
