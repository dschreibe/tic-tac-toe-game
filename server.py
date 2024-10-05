import socket
import threading
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s') # make logging more readable


HOST = '127.0.0.1'
PORT = 65432
RUNNING = True       

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
    start_server()
