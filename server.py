import socket
import threading
import logging
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s') # make logging more readable


HOST = '127.0.0.1'
PORT = 65432
RUNNING = True       

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

def handle_client(conn, addr):
    logging.info(f"New connection from {addr}")
    try:
        while True:
            message = conn.recv(1024)
            if not message:
                break
            # later on can use this to communicate tic tac toe moves
            logging.info(f"Received message from {addr}: {message.decode('utf-8')}")

            conn.sendall(message)
    except socket.error as e:
        logging.error(f"Socket error with {addr}: {e}")
    finally:
        conn.close()
        logging.info(f"Connection closed with {addr}")

def start_server():
    global RUNNING
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    server_socket.settimeout(1)  # check for shutdown
    logging.info(f"Server started, listening on {HOST}:{PORT}")

    try:
        while RUNNING:
            try:
                conn, addr = server_socket.accept()
                client_thread = threading.Thread(target=handle_client, args=(conn, addr))
                client_thread.start()
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
