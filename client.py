import socket
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

HOST = '127.0.0.1'  # Server's IP address
PORT = 65432  # Port the server is listening on

def connect_to_server():
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((HOST, PORT))
        logging.info(f"Connected to server at {HOST}:{PORT}")

        while True:
            message = input("Enter message to send: ")
            if message.lower() == 'exit':
                break
            client_socket.sendall(message.encode('utf-8'))

            response = client_socket.recv(1024)
            if not response:
                logging.info("Connection closed by server.")
                break
            logging.info(f"Received from server: {response.decode('utf-8')}")
    except ConnectionRefusedError:
        logging.error("Connection failed. Server may be unavailable.")
    except socket.error as e:
        logging.error(f"Socket error: {e}")
    finally:
        client_socket.close()
        logging.info("Disconnected from server.")

if __name__ == "__main__":
    connect_to_server()
