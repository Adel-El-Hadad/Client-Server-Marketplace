import threading
import time
import socket
import logging
from threading import Lock
from classes.registration import Register, Registered, RegisterDenied, DeRegister
from classes.searching import (
    LookingFor,
    Offer,
    Found,
    NotAvailable,
    Negotiate,
    Accept,
    Refuse,
    Reserve,
    Cancel,
    Buy,
)
from classes.finalize import InformReq, InformRes, Cancel, ShippingInfo


class ServerRequestHandler(threading.Thread):
    def __init__(self, message, client_address, registered_clients, ongoing_requests,
                offers_by_rq, udp_socket, tcp_port, clients_lock, requests_lock, offers_lock):
        super().__init__()
        self.message = message
        self.client_address = client_address
        self.registered_clients = registered_clients
        self.ongoing_requests = ongoing_requests
        self.offers_by_rq = offers_by_rq
        self.udp_socket = udp_socket
        self.tcp_port = tcp_port
        self.clients_lock = clients_lock
        self.requests_lock = requests_lock
        self.offers_lock = offers_lock
        self.buyer_rq_map = {}  #  for tracking buyer RQs
        if message:  # Only set message_type if message exists (for UDP)
            self.message_type = self.get_message_type()
        self.request_types = {
            "REGISTER": self.register,
            "DE-REGISTER": self.deregister,
            "LOOKING_FOR": self.search_item,
            "OFFER": self.handle_offer,
            "NEGOTIATE": self.negotiate,
            "ACCEPT": self.accept,
            "REFUSE": self.refuse,
            "CANCEL": self.cancel,
            "BUY": self.buy,
            "RESET": self.reset,
        }

    def handle_tcp_connection(self, tcp_client, tcp_address):
        """Handle incoming TCP connections and messages."""
        try:
            while True:
                message = tcp_client.recv(1024).decode('utf-8')
                if not message:
                    break
                
                logging.info(f"Received TCP message from {tcp_address}: {message}")
                
                # Process TCP messages (like INFORM_RES)
                parts = message.split()
                if len(parts) >= 1:
                    message_type = parts[0]
                    if message_type == "INFORM_RES":
                        self.handle_inform_res(parts, tcp_client, tcp_address)
                    else:
                        logging.warning(f"Unknown TCP message type: {message_type}")
                        
        except Exception as e:
            logging.error(f"Error handling TCP connection from {tcp_address}: {e}")
        finally:
            tcp_client.close()
            logging.info(f"TCP connection from {tcp_address} closed")

    def handle_inform_res(self, parts, tcp_client, tcp_address):
        """Handle INFORM_RES messages received via TCP."""
        if len(parts) < 6:
            logging.error("Invalid INFORM_RES format")
            return
        
        rq, name, cc_number, cc_exp_date = parts[1], parts[2], parts[3], parts[4]
        address = ' '.join(parts[5:])  # Address might contain spaces
        
        logging.info(f"INFORM_RES received: RQ={rq}, Name={name}, Address={address}")
        
        # Store the information for transaction processing
        # You can implement additional logic here based on your transaction flow
        
        # Send acknowledgment back to client
        ack_message = f"INFORM_RES_ACK {rq}"
        tcp_client.send(ack_message.encode('utf-8'))
    
    def get_message_type(self):
        """Extract the type of the message from the received data."""
        return self.message.split()[0]

    def run(self):
        """Process the request based on its type."""
        try:
            if self.message_type in self.request_types:
                self.request_types[self.message_type]()
            else:
                print(f"Unknown message type: {self.message_type}")
                self.send_response(f"ERROR: Unknown message type: {self.message_type}")
        except Exception as e:
            print(f"Error processing request: {e}")
            self.send_response(f"ERROR: {e}")

    def send_response(self, response):
        """Send a response back to the client."""
        try:
            self.udp_socket.sendto(str(response).encode('utf-8'), self.client_address)
        except Exception as e:
            print(f"Error sending UDP response: {e}")

    def reset(self):
        """Handle RESET command."""
        with self.clients_lock, self.requests_lock, self.offers_lock:
            self.registered_clients.clear()
            self.ongoing_requests.clear()
            self.offers_by_rq.clear()
        response = "SERVER RESET SUCCESS"
        print(response)
        self.send_response(response)

    def validate_message(self, expected_args_count):
        """Validate the incoming message format."""
        parts = self.message.split()
        if len(parts) < expected_args_count:
            self.send_response(f"ERROR: Invalid message format. Expected {expected_args_count} arguments.")
            return False
        return True

    def register(self):
        """Handle REGISTER requests."""
        data = self.message.split()
        register_request = Register(*data[1:])
    
        with self.clients_lock:
            if register_request.name in self.registered_clients:
                response = RegisterDenied(register_request.rq, "Name already in use")
            else:
                # Generate a unique RQ# on the server
                server_rq = len(self.registered_clients) + 1
            
                # Store client details
                self.registered_clients[register_request.name] = {
                "ip": register_request.ip_address,
                "udp_socket": register_request.udp_socket,
                "tcp_socket": register_request.tcp_socket,
                "rq": server_rq,  # Track the RQ# for this registration
                "address": ""  # Initialize empty address, will be filled during transaction
                }
            
                # Respond with a unique RQ#
                response = Registered(server_rq)
    
        self.send_response(response)

    def deregister(self):
            """Handle DE-REGISTER requests."""
            data = self.message.split()
            deregister_request = DeRegister(*data[1:])
            with self.clients_lock:
                if deregister_request.name in self.registered_clients:
                    del self.registered_clients[deregister_request.name]
                    response = f"DE-REGISTERED {deregister_request.rq}"
                else:
                    response = f"DE-REGISTER-DENIED {deregister_request.rq} Name not registered"
            self.send_response(response)

    def search_item(self):
        """
        Handle LOOKING_FOR requests from the buyer.
        Broadcasts the search to all other clients, collects offers, and processes them.
        """
        data = self.message.split()
        buyer_rq = data[1]  # Extract the original buyer RQ
        search_request = LookingFor(*data[1:])

        # Generate a unique RQ# for the SEARCH message
        search_rq = f"SEARCH-{int(time.time() * 1000)}"

        # Store the search request and its mapping
        with self.requests_lock:
            self.ongoing_requests[search_rq] = search_request
        with self.offers_lock:
            self.offers_by_rq[search_rq] = []

        # Map buyer_rq to the generated search_rq
        self.buyer_rq_map[search_rq] = buyer_rq
        logging.info(f"Mapped buyer_rq {buyer_rq} to search_rq {search_rq}")

        # Broadcast SEARCH to other clients
        with self.clients_lock:
            for client_name, client_info in self.registered_clients.items():
                if client_name != search_request.name:
                    search_message = f"SEARCH {search_rq} {search_request.item_name} {search_request.item_description} {search_request.name}"
                    self.udp_socket.sendto(search_message.encode("utf-8"), (client_info["ip"], int(client_info["udp_socket"])))

        logging.info(f"SEARCH request {search_rq} sent to clients.")

        # Collect offers after a timeout
        print("Waiting for offers...")
        offers = self.collect_responses(search_rq, timeout=60)  

        if offers:
            # Process the collected offers
            print(f"Offers received: {[(o.name, o.price) for o in offers]}")
            self.process_offers(buyer_rq, search_rq, offers, search_request.max_price)
        else:
            # Handle case where no offers are received
            print(f"No offers received for {search_request.item_name}")
            not_available = NotAvailable(buyer_rq, search_request.item_name)
            buyer_info = self.registered_clients.get(search_request.name)
            if buyer_info:
                self.udp_socket.sendto(str(not_available).encode('utf-8'),
                                    (buyer_info["ip"], int(buyer_info["udp_socket"])))

    def process_offers(self, buyer_rq, search_rq, offers, max_price):
        """
        Process the collected offers, selecting the best one within the buyer's max price.
        """
        # Find the lowest-priced offer
        lowest_offer = min(offers, key=lambda o: int(o.price))
        logging.info(f"Lowest offer: {lowest_offer.name} with price {lowest_offer.price}")

        if int(lowest_offer.price) <= int(max_price):
            # Finalize the deal if the offer is within the buyer's budget
            logging.info("Offer within buyer's max price, finalizing deal.")
            self.reserve_and_inform_buyer(search_rq, lowest_offer)
        else:
            # Start negotiation if the lowest offer exceeds the max price
            logging.info(f"Negotiating with seller {lowest_offer.name} for price {max_price}")
            negotiate_message = Negotiate(lowest_offer.rq, lowest_offer.item_name, max_price)
            with self.clients_lock:
                seller_info = self.registered_clients.get(lowest_offer.name)
                if seller_info:
                    self.udp_socket.sendto(
                        str(negotiate_message).encode('utf-8'),
                        (seller_info["ip"], int(seller_info["udp_socket"])),
                    )

    def reserve_and_inform_buyer(self, search_rq, lowest_offer):
        # Retrieve buyer_rq using the mapping
        buyer_rq = self.buyer_rq_map.get(search_rq)
        if not buyer_rq:
            logging.error(f"Error: Buyer request for search_rq {search_rq} not found.")
            return

        # Reserve the item with the seller
        reserve_message = Reserve(lowest_offer.rq, lowest_offer.item_name, lowest_offer.price)
        with self.clients_lock:
            seller_info = self.registered_clients.get(lowest_offer.name)
            if seller_info:
                self.udp_socket.sendto(
                    str(reserve_message).encode('utf-8'),
                    (seller_info["ip"], int(seller_info["udp_socket"])),
                )
                logging.info(f"Sent RESERVE message to seller {lowest_offer.name}")

        # Inform the buyer
        buyer_request = self.ongoing_requests.get(search_rq)
        buyer_info = self.registered_clients.get(buyer_request.name) if buyer_request else None
        if buyer_info:
            found_message = Found(buyer_rq, lowest_offer.item_name, lowest_offer.price)
            self.udp_socket.sendto(
                str(found_message).encode('utf-8'),
                (buyer_info["ip"], int(buyer_info["udp_socket"])),
            )
            logging.info(f"Informed buyer {buyer_request.name} about item availability.")

    def handle_offer(self):
        """Handle OFFER responses."""
        data = self.message.split()
        offer = Offer(*data[1:])
        with self.requests_lock:
            if offer.rq in self.ongoing_requests:
                with self.offers_lock:
                    self.offers_by_rq[offer.rq].append(offer)
            else:
                error_message = f"ERROR: Request {offer.rq} does not exist or has been canceled."
                self.send_response(error_message)

    def negotiate(self):
        """Handle NEGOTIATE responses."""
        data = self.message.split()
        negotiate_request = Negotiate(*data[1:])
        with self.requests_lock:
            search_request = self.ongoing_requests.get(negotiate_request.rq)
        if search_request:
            seller_info = self.registered_clients.get(negotiate_request.name)
            if seller_info:
                # Send NEGOTIATE message to the seller
                negotiate_message = f"NEGOTIATE {negotiate_request.rq} {negotiate_request.item_name} {negotiate_request.max_price}"
                self.udp_socket.sendto(negotiate_message.encode('utf-8'),
                                   (seller_info["ip"], int(seller_info["udp_socket"])))
            else:
                print(f"Seller {negotiate_request.name} not found for RQ {negotiate_request.rq}")
        else:
            print(f"Search request {negotiate_request.rq} not found.")

    def accept(self):
        """
        Handle ACCEPT responses from the seller.
        """
        data = self.message.split()
        accept_request = Accept(*data[1:])  

        with self.requests_lock:
            # Retrieve the corresponding search request
            search_request = self.ongoing_requests.get(accept_request.rq)
            if not search_request:
                self.send_response(f"ERROR: Request {accept_request.rq} does not exist or has been canceled.")
                return

        with self.offers_lock:
            # Retrieve all offers for this RQ
            offers = self.offers_by_rq.get(accept_request.rq, [])
            # Find the lowest price offer
            lowest_offer = min(offers, key=lambda o: int(o.price), default=None)

        if not lowest_offer or lowest_offer.item_name != accept_request.item_name:
            self.send_response(f"ERROR: No valid offer found for RQ#: {accept_request.rq}")
            return

        # Get seller and buyer info
        with self.clients_lock:
            seller_info = self.registered_clients.get(lowest_offer.name)
            buyer_info = self.registered_clients.get(search_request.name)

        if not seller_info or not buyer_info:
            self.send_response(f"ERROR: Seller or Buyer not registered for RQ#: {accept_request.rq}")
            return

        # Reserve the item with the seller offering the lowest price
        reserve = Reserve(accept_request.rq, accept_request.item_name, accept_request.max_price)
        self.udp_socket.sendto(
            str(reserve).encode('utf-8'),
            (seller_info["ip"], int(seller_info["udp_socket"])),
        )
        print(f"Reserved item with seller {lowest_offer.name} at price {accept_request.max_price}")

        # Inform the buyer
        found = Found(accept_request.rq, accept_request.item_name, accept_request.max_price)
        self.udp_socket.sendto(
            str(found).encode('utf-8'),
            (buyer_info["ip"], int(buyer_info["udp_socket"])),
        )
        print(f"Informed buyer {search_request.name} about item availability at price {accept_request.max_price}")
        
    def refuse(self):
        """
        Handle REFUSE responses from the seller.
        """
        data = self.message.split()
        refuse_request = Refuse(*data[1:])

        with self.requests_lock:
            # Retrieve the corresponding search request using the RQ#
            search_request = self.ongoing_requests.get(refuse_request.rq)
            if not search_request:
                self.send_response(f"ERROR: Request {refuse_request.rq} does not exist or has been canceled.")
                return

        # Inform the buyer that the item is not available at the maximum price
        not_found = NotAvailable(search_request.rq, refuse_request.item_name)
        buyer_info = self.registered_clients.get(search_request.name)
        if buyer_info:
            self.udp_socket.sendto(str(not_found).encode('utf-8'),
                               (buyer_info["ip"], int(buyer_info["udp_socket"])))

    def cancel(self):
        """Handle CANCEL requests from the buyer or seller."""
        data = self.message.split()
        cancel_request = Cancel(*data[1:])
        with self.requests_lock:
            if cancel_request.rq in self.ongoing_requests:
                del self.ongoing_requests[cancel_request.rq]
                response = f"CANCELED {cancel_request.rq} for {cancel_request.item_name}"
            else:
                response = f"ERROR: No ongoing request found for RQ: {cancel_request.rq}"

        with self.clients_lock:
            seller_info = self.registered_clients.get(cancel_request.name)
            if seller_info:
                self.udp_socket.sendto(response.encode('utf-8'),
                                    (seller_info["ip"], int(seller_info["udp_socket"])))

    def buy(self):
        """
        Handle BUY requests - Fixed version with proper error handling.
        """
        data = self.message.split()
        if len(data) < 4:
            self.send_response("ERROR: Invalid BUY message format.")
            return

        buy_request = Buy(*data[1:])
        
        # Find the search request
        with self.requests_lock:
            # Look for the search request that matches this buy request
            search_request = None
            for rq, req in self.ongoing_requests.items():
                if (isinstance(req, LookingFor) and 
                    req.item_name == buy_request.item_name and 
                    req.name in self.registered_clients):
                    search_request = req
                    search_rq = rq
                    break

        if not search_request:
            self.send_response(f"ERROR: No matching search request found for item {buy_request.item_name}")
            return

        # Get buyer info
        buyer_info = self.registered_clients.get(search_request.name)
        if not buyer_info:
            self.send_response("ERROR: Buyer not registered.")
            return

        # Find the reserved offer
        with self.offers_lock:
            offers = self.offers_by_rq.get(search_rq, [])
            reserved_offer = None
            for offer in offers:
                if (offer.item_name == buy_request.item_name and 
                    int(offer.price) == int(buy_request.price)):
                    reserved_offer = offer
                    break

        if not reserved_offer:
            self.send_response(f"ERROR: No matching offer found for item {buy_request.item_name} at price {buy_request.price}")
            return

        # Get seller info
        seller_info = self.registered_clients.get(reserved_offer.name)
        if not seller_info:
            self.send_response("ERROR: Seller not found.")
            return

        # Initiate TCP transaction
        try:
            buyer_response, seller_response = self.initiate_tcp_transaction(
                buyer_info, seller_info, buy_request.item_name, buy_request.price
            )

            if not buyer_response or not seller_response:
                self.cancel_transaction(
                    buy_request.rq, buyer_info, seller_info, "Failed to retrieve transaction information"
                )
                return

            # Process the responses (extract information for payment)
            buyer_parts = buyer_response.split()
            seller_parts = seller_response.split()
            
            if len(buyer_parts) < 6 or len(seller_parts) < 6:
                self.cancel_transaction(
                    buy_request.rq, buyer_info, seller_info, "Invalid transaction information format"
                )
                return

            # Extract buyer and seller information
            buyer_cc = buyer_parts[3] if len(buyer_parts) > 3 else "unknown"
            seller_cc = seller_parts[3] if len(seller_parts) > 3 else "unknown"
            buyer_address = ' '.join(buyer_parts[5:]) if len(buyer_parts) > 5 else "unknown"

            # Simulate payment processing
            if not self.simulate_payment(buyer_cc, seller_cc, buy_request.price):
                self.cancel_transaction(buy_request.rq, buyer_info, seller_info, "Payment processing failed")
                return

            # Send shipping information to seller
            shipping_info = ShippingInfo(buy_request.rq, search_request.name, buyer_address)
            self.send_tcp_message(seller_info["ip"], int(seller_info["tcp_socket"]), str(shipping_info))

            # Send success response to buyer
            self.send_response(f"TRANSACTION_SUCCESS {buy_request.rq} {buy_request.item_name} {buy_request.price}")
            
            # Clean up
            with self.requests_lock:
                if search_rq in self.ongoing_requests:
                    del self.ongoing_requests[search_rq]
            with self.offers_lock:
                if search_rq in self.offers_by_rq:
                    del self.offers_by_rq[search_rq]
            
            print(f"Transaction {buy_request.rq} completed successfully.")
            
        except Exception as e:
            logging.error(f"Error during BUY transaction: {e}")
            self.cancel_transaction(buy_request.rq, buyer_info, seller_info, f"Transaction error: {str(e)}")

    def initiate_tcp_transaction(self, buyer_info, seller_info, item_name, price):
        """Handle transaction details over TCP."""
        buyer_response = None
        seller_response = None
        
        try:
            # Connect to buyer and seller
            buyer_tcp = (buyer_info["ip"], int(buyer_info["tcp_socket"]))
            seller_tcp = (seller_info["ip"], int(seller_info["tcp_socket"]))

            # Send INFORM_REQ to buyer
            inform_message = f"INFORM_REQ {item_name} {price}"
            buyer_response = self.send_tcp_message(buyer_tcp[0], buyer_tcp[1], inform_message)
            
            # Send INFORM_REQ to seller  
            seller_response = self.send_tcp_message(seller_tcp[0], seller_tcp[1], inform_message)

            logging.info(f"Buyer Response: {buyer_response}")
            logging.info(f"Seller Response: {seller_response}")

            return buyer_response, seller_response
            
        except Exception as e:
            logging.error(f"Error during TCP transaction: {e}")
            return None, None

    def send_tcp_message(self, client_ip, client_port, message):
        """Send a message via TCP and return the response."""
        try:
            with socket.create_connection((client_ip, client_port), timeout=10) as tcp_socket:
                tcp_socket.sendall(message.encode('utf-8'))
                response = tcp_socket.recv(1024).decode('utf-8')
                logging.info(f"TCP Response from {client_ip}:{client_port} - {response}")
                return response
        except Exception as e:
            logging.error(f"Error during TCP communication with {client_ip}:{client_port} - {e}")
            return None
    
    def cancel_transaction(self, rq, buyer_info, seller_info, reason):
        """
        Cancel the transaction and notify buyer and seller.
        """
        cancel_message = f"CANCEL {rq} {reason}"

        if buyer_info:
            self.udp_socket.sendto(cancel_message.encode('utf-8'),
                                (buyer_info["ip"], int(buyer_info["udp_socket"])))

        if seller_info:
            self.udp_socket.sendto(cancel_message.encode('utf-8'),
                                (seller_info["ip"], int(seller_info["udp_socket"])))

        # Clean up buyer_rq_map
        self.buyer_rq_map.pop(rq, None)

        print(f"Transaction {rq} cancelled: {reason}")

    def simulate_payment(self, buyer_cc, seller_cc, price):
        """
        Simulate payment processing between buyer and seller.
        """
        try:
            print(f"Processing payment: Charging buyer CC: {buyer_cc}, Crediting seller CC: {seller_cc}")
            seller_amount = int(price) * 0.9  # Deduct 10% transaction fee
            print(f"Payment successful: Seller credited with {seller_amount}")
            return True
        except Exception as e:
            print(f"Payment simulation error: {e}")
            return False

    def collect_responses(self, rq, timeout=30):
        """Collect responses (offers) within the specified timeout period."""
        start_time = time.time()
        collected_offers = []

        while time.time() - start_time < timeout:
            with self.offers_lock:
                collected_offers = self.offers_by_rq.get(rq, [])
            time.sleep(1)  # Allow time for other threads to process offers
        return collected_offers