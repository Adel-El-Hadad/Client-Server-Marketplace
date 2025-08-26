# Client-Server Marketplace
This is a python based terminal application simulating a real-time marketplace. Clients can register, search for items, offer items, negotiate prices, and complete transactions. The system uses UDP and TCP sockets to handle communication between clients and the server, supporting both request-response and direct client-server messaging. 

## System Structure

# Server
1. Handles client registration and reregistration.
2. Processes search requests and item offers.
3. Manages transactions.
4. Listens on UDP and TCP ports.

# Client
1. Terminal- based interface for the user.
2. Sends commands to the server: register, look for items, offer, buy, cancel.
3. Listens for server messages via UDP and TCP.
4. Handles negotiation and transaction updates.

## Team
1. Adel ElHadad
2. Kareem Mohamed
