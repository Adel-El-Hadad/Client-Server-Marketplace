class InformReq:
    def __init__(self, rq, item_name, price):
        self.TYPE = "INFORM_REQ"
        self.rq = rq
        self.item_name = item_name
        self.price = price

    def __str__(self):
        return f"{self.TYPE} {self.rq} {self.item_name} {self.price}"


class InformRes:
    def __init__(self, rq, name, cc_number, cc_exp_date, address):
        self.TYPE = "INFORM_RES"
        self.rq = rq
        self.name = name
        self.cc_number = cc_number
        self.cc_exp_date = cc_exp_date
        self.address = address

    def __str__(self):
        return f"{self.TYPE} {self.rq} {self.name} {self.cc_number} {self.cc_exp_date} {self.address}"


class Cancel:
    def __init__(self, rq, reason):
        self.TYPE = "CANCEL"
        self.rq = rq
        self.reason = reason

    def __str__(self):
        return f"{self.TYPE} {self.rq} {self.reason}"


class ShippingInfo:
    def __init__(self, rq, name, address):
        self.TYPE = "SHIPPING_INFO"
        self.rq = rq
        self.name = name
        self.address = address

    def __str__(self):
        return f"{self.TYPE} {self.rq} {self.name} {self.address}"
