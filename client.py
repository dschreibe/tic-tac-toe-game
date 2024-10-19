import socket
import logging
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

HOST = None  # Server's IP address or DNS name
PORT = 65432  # Port the server is listening on

def handle_arguments():
    global HOST
    global PORT
    n = len(sys.argv)
    i = 1
    while i < n:
        arg = sys.argv[i]
        if arg == "-h":
            print("Usage:")
            print("-h              Show this help message")
            print("-i Host-IP      Set the host IP address (required)")
            print("-p Host-Port    Set the host port number (default: 65432)")
            print("-n DNS-Name     Set the DNS name of the server")
            sys.exit(0)
        elif arg == "-i":
            if i + 1 < n:
                HOST = sys.argv[i + 1]
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
        elif arg == "-n":
            if i + 1 < n:
                HOST = sys.argv[i + 1]
                i += 1
            else:
                print("Error: -n requires a DNS name")
                sys.exit(1)
        else:
            print(f"Error: Unknown argument '{arg}'")
            print("Use -h for help")
            sys.exit(1)
        i += 1

    if HOST is None:
        print("Error: -i (IP address) is required")
        sys.exit(1)

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
    handle_arguments()
    connect_to_server()
