# Tic-Tac-Toe Game

This is a simple Tic-Tac-Toe game implemented using Python and sockets. The project is console based aiming to work on any computer that runs Python

**How to play:**
1. Run `server.py`
2. Run `client.py` (you can also run multiple clients or just one)
3. On client, type "join" then follow instructions to select username
4. Either on same client or different client, type "join" then follow instructions to select username
  * NOTE: A client can only have one "username" at a time. This means if you are using one client you have to type in "join" to switch between these two usernames to play. If using two clients you can switch between clients when playing without having to type join again.
5. Once two users have joined, on client type "move" and use the first user who joined the game
6. Continue game until there is a winner or draw
7. Once winner or draw is determined new usernames have to be picked!

**How to play (with GUI):**
* Follow same instructions above but add the -g flag
* Can use only one client to play and switch between users but recommended to use two clients.
* After game is over, make sure you click "reset" button to pick new usernames!

**Testing**
* There is a test file that tests a edge cases/basic functionality
* To run tests `pytest -v test.py`

**Technologies used:**
* Python
* Sockets
* Threading
* Logging
* JSON
* Fernet (symmetric encryption)
* tkinter

**Limitations:**
* Only supports one game at a time (can have multiple clients connected at once but only one game can be played at a time)
* Currently there is no checks for if a player "owns" a username and another client could make a move with the same username

**Features**

* State Management:
The server tracks the current game state, including:
The game board.
The player's turn.
The game's status (ongoing, win, draw).
Clients receive regular updates about the game state via game_update messages.
* Input Handling:
Clients validate user input:
Ensures usernames are unique.
Verifies move coordinates are within bounds (0–2).
Prevents invalid moves (e.g., selecting an occupied cell).
* Winning Conditions:
The server determines win/draw conditions and notifies clients via game_result messages.
Winning moves are logged, and the winner's username is displayed.
* Game-Over Handling:
Clients display the result and allow users to start a new game by rejoining with a username.
* User Interface:
Text-based, console UI:
Displays the board in a 3x3 grid format after each move.
Shows game results, including the winner or a draw message.
Provides logs for actions like moves, chat messages, and errors.

**Security/Risk Evaluation**

One of the main issues with the encryption is the possibility of man in the middle attacks. This could be fixed by using a certificate authority. As stated in the limitations, the server also doesn't let clients "own" a username so another client could switch their username and impersonate another user. A future implementation of this game could include safe guards against man in the middle attacks. 


**Additional resources:**
* [Socket example](https://www.geeksforgeeks.org/socket-programming-python/)


**Game Message Protocol**
* Use JSON to send messages between clients and server.

General format

```
{
  "type": "message_type",
  "data": {
    "field1": "value",
    "field2": "value"
  }
} 
```

Join Game (required before beginning)
```
{
  "type": "join",
  "data": {
    "username": "player1"
  }
}
```

Player Move (Represents a player's move during the game)
```
{
  "type": "move",
  "data": {
    "username": "player1",
    "position": {
      "row": 1,
      "col": 2
    }
  }
}
```
Chat Message (Players can send messages)
```
{
  "type": "chat",
  "data": {
    "username": "player1",
    "message": "message1"
  }
}
```
Quit Game (Remove player from game)
```
{
  "type": "quit",
  "data": {
    "username": "player1"
  }
}
```
**Server responses**

Game State
```
{
  "type": "game_update",
  "data": {
    "board": [
      ["X", "O", "X"],
      ["O", "X", "O"],
      ["", "", "X"]
    ],
    "next_turn": "player2",
    "status": "ongoing" // ongoing, draw, win
  }
}
```
Move Acknowledgment
```
{
  "type": "move_ack",
  "data": {
    "success": true,
    "message": "Move successful."
  }
}
```
Game Result
```
{
  "type": "game_result",
  "data": {
    "result": "win", // win, draw
    "winner": "player1"
  }
}
```
Errors (Maybe expand to include more errors)
```
{
  "type": "error",
  "data": {
    "message": "Invalid move. Cell already occupied."
  }
}
```
