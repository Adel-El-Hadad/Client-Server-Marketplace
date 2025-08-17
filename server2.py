import socket
import threading
import time
from threading import Lock
from serverRequest import ServerRequestHandler  # Import the handler
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Log all levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
    format='%(asctime)s - %(levelname)s - %(message)s',  # Include timestamp and log level
    handlers=[
        logging.FileHandler("server.log"),  # Log to a file
        logging.StreamHandler()            # Log to the console
    ]
)

# Global flag to stop threads
server_running = True

# Server Configuration
SERVER_IP = "127.0.0.1"
SERVER_PORT = 5005
TCP_PORT = 5006  # Dedicated TCP port for TCP connections

# In-memory data storage with locks
registered_clients = {}  # Stores registered clients
ongoing_requests = {}  # Tracks ongoing item requests
offers_by_rq = {}  # Tracks offers by request number

clients_lock = Lock()
requests_lock = Lock()
offers_lock = Lock()

# UDP Server Socket Setup
udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_socket.bind((SERVER_IP, SERVER_PORT))
logging.info(f"UDP Server started at {SERVER_IP}:{SERVER_PORT}")

# TCP Server Socket Setup
tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Allow port reuse
tcp_socket.bind((SERVER_IP, TCP_PORT))
tcp_socket.listen(5)  # Maximum 5 simultaneous TCP connections
logging.info(f"TCP Server listening on {SERVER_IP}:{TCP_PORT}")

def handle_tcp_client(tcp_client, tcp_address):
    """Handle individual TCP client connection."""
    try:
        handler = ServerRequestHandler(
            message=None,  # No UDP message for TCP connections
            client_address=tcp_address,
            registered_clients=registered_clients,
            ongoing_requests=ongoing_requests,
            offers_by_rq=offers_by_rq,
            udp_socket=udp_socket,  # Pass UDP socket for sending responses
            tcp_port=TCP_PORT,
            clients_lock=clients_lock,
            requests_lock=requests_lock,
            offers_lock=offers_lock,
        )
        handler.handle_tcp_connection(tcp_client, tcp_address)
    except Exception as e:
        logging.error(f"Error handling TCP client {tcp_address}: {e}")
    finally:
        tcp_client.close()

def handle_tcp_connections():
    """Accept and handle incoming TCP connections."""
    try:
        while server_running:
            try:
                tcp_client, tcp_address = tcp_socket.accept()
                logging.info(f"New TCP connection from {tcp_address}")

                # Create a thread to handle the TCP connection
                tcp_thread = threading.Thread(
                    target=handle_tcp_client,
                    args=(tcp_client, tcp_address),
                    daemon=True
                )
                tcp_thread.start()
                
            except Exception as e:
                if server_running:  # Only log if server is supposed to be running
                    logging.error(f"Error accepting TCP connection: {e}")
                break
    except Exception as e:
        logging.error(f"TCP server error: {e}")
    finally:
        tcp_socket.close()
        logging.info("TCP socket closed.")

def handle_udp_messages():
    """Handle incoming UDP messages."""
    try:
        while server_running:
            try:
                udp_socket.settimeout(1.0)  # Set timeout to allow periodic checks
                message, client_address = udp_socket.recvfrom(1024)
                logging.info(f"Received UDP message from {client_address}: {message.decode('utf-8')}")
                
                # Create handler for UDP message
                handler = ServerRequestHandler(
                    message.decode("utf-8"),
                    client_address,
                    registered_clients,
                    ongoing_requests,
                    offers_by_rq,
                    udp_socket,
                    TCP_PORT,
                    clients_lock,
                    requests_lock,
                    offers_lock,
                )
                handler.start()
                
            except socket.timeout:
                # Timeout is normal, continue loop
                continue
            except Exception as e:
                if server_running:
                    logging.error(f"Error handling UDP message: {e}")
    except Exception as e:
        logging.error(f"UDP server error: {e}")
    finally:
        udp_socket.close()
        logging.info("UDP socket closed.")

def shutdown_server():
    """Gracefully shutdown the server."""
    global server_running
    server_running = False
    
    # Close sockets
    try:
        udp_socket.close()
    except:
        pass
    
    try:
        tcp_socket.close()
    except:
        pass
    
    logging.info("Server shutdown initiated.")

# Main server entry point
if __name__ == "__main__":
    try:
        # Start UDP and TCP handling threads
        udp_thread = threading.Thread(target=handle_udp_messages, daemon=True)
        tcp_thread = threading.Thread(target=handle_tcp_connections, daemon=True)

        udp_thread.start()
        tcp_thread.start()

        logging.info("Server threads started. UDP and TCP handlers are running.")
        logging.info("Press Ctrl+C to stop the server.")

        # Keep main thread alive
        try:
            while server_running:
                time.sleep(1)  # Simple sleep instead of join with timeout
                if not udp_thread.is_alive() or not tcp_thread.is_alive():
                    logging.warning("One of the server threads has stopped unexpectedly.")
                    break
        except KeyboardInterrupt:
            logging.info("Keyboard interrupt received.")
            
    except KeyboardInterrupt:
        logging.info("\nServer shutting down...")
    except Exception as e:
        logging.error(f"Server startup error: {e}")
    finally:
        shutdown_server()
        logging.info("Server shutdown complete.")