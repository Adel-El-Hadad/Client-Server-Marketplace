class Register:
    def __init__(self, rq, name, ip_address, udp_socket, tcp_socket):
        self.TYPE = "REGISTER"
        self.rq = rq
        self.name = name
        self.ip_address = ip_address
        self.udp_socket = udp_socket
        self.tcp_socket = tcp_socket

    def __str__(self):
        return f"{self.TYPE} {self.rq} {self.name} {self.ip_address} {self.udp_socket} {self.tcp_socket}"


class Registered:
    def __init__(self, rq):
        self.TYPE = "REGISTERED"
        self.rq = rq

    def __str__(self):
        return f"{self.TYPE} {self.rq}"


class RegisterDenied:
    def __init__(self, rq, reason):
        self.TYPE = "REGISTER-DENIED"
        self.rq = rq
        self.reason = reason

    def __str__(self):
        return f"{self.TYPE} {self.rq} {self.reason}"


class DeRegister:
    def __init__(self, rq, name):
        self.TYPE = "DE-REGISTER"
        self.rq = rq
        self.name = name

    def __str__(self):
        return f"{self.TYPE} {self.rq} {self.name}"
