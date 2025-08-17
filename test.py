import socket
import threading
import select
import time

SERVER_IP = '127.0.0.1'
SERVER_PORT = 5005
TCP_PORT = 5006  # TCP port for additional functionality

# Internal configuration
request_counter = 1  # Tracks request numbers for the client
client_name = None  # Client's name
client_udp_port = None  # UDP port for this client
client_tcp_port = None  # TCP port for this client
tcp_server_socket = None  # TCP server socket for listening
udp_socket = None  # Global UDP socket

def send_command_with_response(command):
    """
    Sends a command to the server and returns the server's response.
    """
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.settimeout(60)  # Timeout for server response
    try:
        client_socket.sendto(command.encode('utf-8'), (SERVER_IP, SERVER_PORT))
        response, _ = client_socket.recvfrom(1024)
        return response.decode('utf-8')
    except socket.timeout:
        print("Server is not responding. Please try again later.")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None
    finally:
        client_socket.close()

def send_command(command):
    """
    Sends a command to the server and prints the response.
    """
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.settimeout(120)  # Timeout for server response
    try:
        client_socket.sendto(command.encode('utf-8'), (SERVER_IP, SERVER_PORT))
        response, _ = client_socket.recvfrom(1024)
        print(f"Server response: {response.decode('utf-8')}")
    except socket.timeout:
        print("Server is not responding. Please try again later.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client_socket.close()

def setup_tcp_server():
    """Setup TCP server to listen for incoming connections from the main server."""
    global tcp_server_socket, client_tcp_port
    
    try:
        tcp_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        tcp_server_socket.bind(('127.0.0.1', 0))  # OS chooses available port
        client_tcp_port = tcp_server_socket.getsockname()[1]
        tcp_server_socket.listen(5)
        
        print(f"Client TCP server listening on port {client_tcp_port}")
        
        # Start TCP listener thread
        tcp_listener = threading.Thread(target=handle_tcp_connections, daemon=True)
        tcp_listener.start()
        
        return True
    except Exception as e:
        print(f"Error setting up TCP server: {e}")
        return False

def handle_tcp_connections():
    """Handle incoming TCP connections from the server."""
    global tcp_server_socket
    
    while True:
        try:
            if tcp_server_socket:
                client_conn, addr = tcp_server_socket.accept()
                print(f"TCP connection accepted from {addr}")
                
                # Handle the connection in a separate thread
                conn_thread = threading.Thread(
                    target=handle_tcp_client, 
                    args=(client_conn, addr), 
                    daemon=True
                )
                conn_thread.start()
        except Exception as e:
            print(f"Error accepting TCP connection: {e}")
            break

def handle_tcp_client(client_conn, addr):
    """Handle individual TCP client connection."""
    try:
        while True:
            message = client_conn.recv(1024).decode('utf-8')
            if not message:
                break
                
            print(f"\nTCP Message from {addr}: {message}")
            
            # Process the message
            parts = message.split()
            if len(parts) >= 1:
                message_type = parts[0]
                
                if message_type == "INFORM_REQ":
                    response = handle_inform_req(parts)
                    if response:
                        client_conn.send(response.encode('utf-8'))
                elif message_type == "SHIPPING_INFO":
                    handle_shipping_info(parts)
                elif message_type == "CANCEL":
                    print(f"Transaction cancelled: {' '.join(parts[1:])}")
                else:
                    print(f"Unknown TCP message type: {message_type}")
                    
    except Exception as e:
        print(f"Error handling TCP client {addr}: {e}")
    finally:
        client_conn.close()

def handle_inform_req(parts):
    """
    Handles the INFORM_REQ message from the server and returns INFORM_RES.
    """
    if len(parts) < 4:
        print("Invalid INFORM_REQ message format.")
        return None

    # Extract item name and price (RQ might not be present in some formats)
    try:
        if parts[1].isdigit():  # If second part is RQ number
            rq, item_name, price = parts[1], parts[2], parts[3]
        else:  # If no RQ number
            item_name, price = parts[1], parts[2]
            rq = "1"  # Default RQ
    except IndexError:
        print("Error parsing INFORM_REQ message")
        return None

    print(f"INFORM_REQ received for Item={item_name}, Price={price}")

    # Collect buyer/seller details
    cc_number = input("Enter your credit card number: ").strip()
    if not cc_number:
        cc_number = "4111111111111111"  # Default for testing
        
    cc_exp_date = input("Enter credit card expiry date (MM/YY): ").strip()
    if not cc_exp_date:
        cc_exp_date = "12/25"  # Default for testing
        
    address = input("Enter your address: ").strip()
    if not address:
        address = "123 Main St, City, State"  # Default for testing

    # Send INFORM_RES
    inform_res_response = f"INFORM_RES {rq} {client_name} {cc_number} {cc_exp_date} {address}"
    print(f"Sending: {inform_res_response}")
    return inform_res_response

def handle_shipping_info(parts):
    """
    Handles the SHIPPING_INFO message from the server.
    """
    if len(parts) < 4:
        print("Invalid SHIPPING_INFO message format.")
        return

    rq, buyer_name, buyer_address = parts[1], parts[2], ' '.join(parts[3:])
    print(f"Shipping Info Received: RQ={rq}, Buyer={buyer_name}, Address={buyer_address}")
    print(f"Prepare to ship the item to {buyer_name} at {buyer_address}.")

def handle_negotiation(parts):
    """
    Handles the NEGOTIATE message received from the server.
    """
    rq, item_name, max_price = parts[1], parts[2], parts[3]
    print(f"Negotiation Request: {item_name} for max price {max_price}")
    response = input("Do you accept the price? (yes/no): ").strip().lower()

    if response == "yes":
        command = f"ACCEPT {rq} {item_name} {max_price}"
    else:
        command = f"REFUSE {rq} {item_name} {max_price}"

    send_command(command)

def handle_found(parts):
    """
    Handles the FOUND message received from the server.
    """
    rq, item_name, price = parts[1], parts[2], parts[3]
    print(f"Item Found: {item_name} for price {price}")
    response = input("Do you want to buy the item? (yes/no): ").strip().lower()

    if response == "yes":
        buy_item(rq, item_name, price)
    else:
        cancel_item(rq, item_name, price)
        
def buy_item(rq, item_name, price):
    """
    Sends a BUY request to the server.
    """
    command = f"BUY {rq} {item_name} {price}"
    send_command(command)
    print(f"BUY request sent for {item_name} at {price}.")

def cancel_item(rq, item_name, price):
    """
    Sends a CANCEL request to the server.
    """
    command = f"CANCEL {rq} {item_name} {price}"
    send_command(command)

def listen_for_udp():
    """
    Continuously listens for incoming UDP messages and processes them.
    """
    global udp_socket
    if not udp_socket:
        print("UDP socket is not initialized.")
        return

    print(f"Listening for UDP messages on port {client_udp_port}...")

    while True:
        try:
            # Wait for the socket to be ready for reading
            ready, _, _ = select.select([udp_socket], [], [], 1)
            if ready:
                message, address = udp_socket.recvfrom(1024)
                decoded_message = message.decode('utf-8')
                print(f"\nUDP Message from {address}: {decoded_message}")
                process_message(decoded_message)
        except Exception as e:
            print(f"Error receiving UDP message: {e}")
            break

def process_message(message):
    """
    Process a specific UDP message based on its type.
    """
    parts = message.split()
    if len(parts) == 0:
        return
        
    message_type = parts[0]
    
    if message_type == "SEARCH":
        handle_search(parts)
    elif message_type == "RESERVE":
        handle_reserve(parts)
    elif message_type == "FOUND":
        handle_found(parts)
    elif message_type == "NEGOTIATE":
        handle_negotiation(parts)
    elif message_type == "NOT_AVAILABLE":
        handle_not_available(parts)
    elif message_type == "ACCEPT":
        print(f"Item accepted for sale: {parts[1:]}")
    elif message_type == "REFUSE":
        handle_refuse(parts)
    elif message_type == "TRANSACTION_SUCCESS":
        handle_transaction_success(parts)
    elif message_type == "CANCEL":
        print(f"Transaction cancelled: {' '.join(parts[1:])}")

def handle_search(parts):
    """
    Handle incoming SEARCH messages.
    """
    if len(parts) < 5:
        print("Invalid SEARCH message format.")
        return
        
    search_rq, item_name, item_description, requester_name = parts[1], parts[2], parts[3], parts[4]
    print(f"\nSEARCH received: {item_name} ({item_description}) requested by {requester_name}")
    print("You can respond by choosing option 4 (Offer an item) from the menu.")

def handle_reserve(parts):
    """
    Handles the RESERVE message from the server.
    """
    if len(parts) < 4:
        print("Invalid RESERVE message format.")
        return
        
    rq, item_name, price = parts[1], parts[2], parts[3]
    print(f"Item reserved: RQ={rq}, Item={item_name}, Price={price}")

def handle_not_available(parts):
    """
    Handles the NOT_AVAILABLE message from the server.
    """
    if len(parts) < 3:
        print("Invalid NOT_AVAILABLE message format.")
        return
        
    rq, item_name = parts[1], parts[2]
    print(f"Item NOT AVAILABLE: RQ={rq}, Item={item_name}")

def handle_refuse(parts):
    """
    Handles the REFUSE message from the server.
    """
    if len(parts) < 2:
        print("Invalid REFUSE message format.")
        return

    rq = parts[1]
    print(f"Sale refused for RQ={rq}.")

def handle_transaction_success(parts):
    """
    Handles the TRANSACTION_SUCCESS message from the server.
    """
    if len(parts) < 4:
        print("Invalid TRANSACTION_SUCCESS message format.")
        return
        
    rq, item_name, price = parts[1], parts[2], parts[3]
    print(f"🎉 TRANSACTION SUCCESSFUL! RQ={rq}, Item={item_name}, Price={price}")

def register():
    """
    Registers the client with the server.
    """
    global client_name, client_udp_port, client_tcp_port, request_counter, udp_socket

    if client_name:
        print(f"You are already registered as {client_name}.")
        return

    name = input("Enter your name: ").strip().lower()
    if not name:
        print("Name cannot be empty.")
        return

    # Setup TCP server first
    if not setup_tcp_server():
        print("Failed to setup TCP server. Registration aborted.")
        return

    # Initialize and bind the global UDP socket
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind(('127.0.0.1', 0))  # OS chooses an available port
    client_udp_port = udp_socket.getsockname()[1]

    command = f"REGISTER {request_counter} {name} 127.0.0.1 {client_udp_port} {client_tcp_port}"
    response = send_command_with_response(command)

    if response and response.startswith("REGISTERED"):
        print(response)
        client_name = name  # Set the client name only on success
        
        # Start UDP listener
        udp_listener = threading.Thread(target=listen_for_udp, daemon=True)
        udp_listener.start()
    elif response and response.startswith("REGISTER-DENIED"):
        print(response)
        client_name = None  # Ensure client_name is not set
        # Close TCP server if registration failed
        if tcp_server_socket:
            tcp_server_socket.close()
    else:
        print("Registration failed. Please try again.")

    request_counter += 1

def deregister():
    """
    Deregisters the client from the server.
    """
    global client_name, request_counter, tcp_server_socket

    if not client_name:
        print("You need to register first.")
        return

    command = f"DE-REGISTER {request_counter} {client_name}"
    response = send_command_with_response(command)

    if response and response.startswith("DE-REGISTERED"):
        print(response)
        client_name = None  # Clear the client name after successful deregistration
        
        # Close TCP server
        if tcp_server_socket:
            tcp_server_socket.close()
            tcp_server_socket = None
    else:
        print(response or "Deregistration failed. Please try again.")

    request_counter += 1

def look_for():
    """
    Sends a LOOKING_FOR request to the server.
    """
    global request_counter

    if not client_name:
        print("You need to register first.")
        return

    item_name = input("Enter the item name: ").strip()
    description = input("Enter a description for the item: ").strip()
    max_price = input("Enter the maximum price you're willing to pay: ").strip()

    if not item_name or not description or not max_price.isdigit():
        print("Invalid input. Please try again.")
        return

    command = f"LOOKING_FOR {request_counter} {client_name} {item_name} {description} {max_price}"
    send_command(command)
    request_counter += 1

def offer():
    """
    Sends an OFFER to the server.
    """
    global request_counter

    if not client_name:
        print("You need to register first.")
        return

    rq = input("Enter the RQ number from the SEARCH request: ").strip()
    if not rq:
        print("RQ number cannot be empty. Please try again.")
        return

    item_name = input("Enter the item name: ").strip()
    price = input("Enter your offer price: ").strip()

    if not item_name or not price.isdigit():
        print("Invalid input. Please try again.")
        return

    command = f"OFFER {rq} {client_name} {item_name} {price}"
    send_command(command)
    print("Offer sent. Waiting for server response...")

def buy():
    """
    Sends a BUY request to the server.
    """
    global request_counter

    if not client_name:
        print("You need to register first.")
        return

    item_name = input("Enter the item name: ").strip()
    price = input("Enter the price of the item: ").strip()

    if not item_name or not price.isdigit():
        print("Invalid input. Please try again.")
        return

    command = f"BUY {request_counter} {item_name} {price}"
    send_command(command)
    request_counter += 1

def cancel():
    """
    Sends a CANCEL request to the server.
    """
    global request_counter

    if not client_name:
        print("You need to register first.")
        return

    item_name = input("Enter the item name to cancel: ").strip()
    price = input("Enter the price of the item to cancel: ").strip()

    if not item_name or not price.isdigit():
        print("Invalid input. Please try again.")
        return

    command = f"CANCEL {request_counter} {item_name} {price}"
    send_command(command)
    request_counter += 1

def reset_server():
    """
    Sends a RESET command to the server.
    """
    command = "RESET"
    send_command(command)
    global client_name, tcp_server_socket
    client_name = None
    if tcp_server_socket:
        tcp_server_socket.close()
        tcp_server_socket = None
    print("The server has been reset. All clients are deregistered.")

def exit_client():
    """
    Gracefully closes sockets and exits the program.
    """
    global tcp_server_socket, udp_socket
    
    if tcp_server_socket:
        tcp_server_socket.close()
    if udp_socket:
        udp_socket.close()
    print("Client exited gracefully.")
    exit()

def menu():
    """
    Displays a menu of options to the user and executes the selected option.
    """
    while True:
        print("\n" + "="*50)
        print("CLIENT-SERVER MARKETPLACE")
        print("="*50)
        print("1. Register")
        print("2. Deregister")
        print("3. Look for an item")
        print("4. Offer an item")
        print("5. Buy an item")
        print("6. Cancel a request")
        print("7. Reset server")
        print("8. Exit")
        print("="*50)
        if client_name:
            print(f"Status: Registered as '{client_name}'")
        else:
            print("Status: Not registered")
        print("="*50)

        choice = input("Enter your choice: ").strip()
        if choice == "1":
            register()
        elif choice == "2":
            deregister()
        elif choice == "3":
            look_for()
        elif choice == "4":
            offer()
        elif choice == "5":
            buy()
        elif choice == "6":
            cancel()
        elif choice == "7":
            reset_server()
        elif choice == "8":
            exit_client()
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    print("Starting Client-Server Marketplace Client...")
    try:
        menu()
    except KeyboardInterrupt:
        print("\nShutting down client...")
        exit_client()