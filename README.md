# File Sharing Server Using Python
## 1. Introduction:
A Local-Host client-server program that stores and send file data from client and sends it to the server or a client shares a file data stored in the server's database to another client.

## 2. Features:
- Login Authentication: *Provides authentication to the username and user's password before logging in to the user's interface.*

- Local Storage: *The users' data are stored by using **key identifier** to separate between other users in the server's database.*

- Multi-threading: *The server can handle multiple users at the same time using **threading**.*

- Sharing: *The user can share his/her files to another user, by typing the name of the other user.*

## 3. Libraries:
1. Socket: *Sending and recieving the file data.*
2. Threading: *To handle multiple users at the same time.*
3. Sqlite3: *To create a database for the server to store the users' data.*

## 4. Configuration:
The configuration of the server is done by:
- Identifying the ip of the local host "127.0.0.1".
- Choosing an empty port for the user, Example: "5555".
- Creating a variable to store the path of the database, to store the client's data.

## 5. Running The Program:
When you run the application, you must:
1. Open the server by using the command: `python3 server.py` in the terminal.
2. Run the client code in the client terminal by using the command: `python3 client.py`.
