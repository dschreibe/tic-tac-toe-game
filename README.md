# Tic-Tac-Toe Game

This is a simple Tic-Tac-Toe game implemented using Python and sockets. The project is console based aiming to work on any computer that runs Python

**How to play:**
1. Run server.py
2. Run client.py (you can also run multiple clients or just one)
3. On client, type "join" then follow instructions to select username
4. Either on same client or different client, type "join" then follow instructions to select username
5. Once two users have joined, on client type move and use the first user who joined the game
6. Continue game until there is a winner or draw
7. Once winner or draw is determined new usernames have to be picked!


**Technologies used:**
* Python
* Sockets
* Threading
* Logging

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
