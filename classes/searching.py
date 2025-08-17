class LookingFor:
    def __init__(self, rq, name, item_name, item_description, max_price):
        self.TYPE = "LOOKING_FOR"
        self.rq = rq
        self.name = name
        self.item_name = item_name
        self.item_description = item_description
        self.max_price = max_price

    def __str__(self):
        return f"{self.TYPE} {self.rq} {self.name} {self.item_name} {self.item_description} {self.max_price}"


class Offer:
    def __init__(self, rq, name, item_name, price):
        self.TYPE = "OFFER"
        self.rq = rq
        self.name = name
        self.item_name = item_name
        self.price = price

    def __str__(self):
        return f"{self.TYPE} {self.rq} {self.name} {self.item_name} {self.price}"


class Found:
    def __init__(self, rq, item_name, price):
        self.TYPE = "FOUND"
        self.rq = rq
        self.item_name = item_name
        self.price = price

    def __str__(self):
        return f"{self.TYPE} {self.rq} {self.item_name} {self.price}"


class NotAvailable:
    def __init__(self, rq, item_name):
        self.TYPE = "NOT_AVAILABLE"
        self.rq = rq
        self.item_name = item_name

    def __str__(self):
        return f"{self.TYPE} {self.rq} {self.item_name}"


class Negotiate:
    def __init__(self, rq, item_name, max_price):
        self.TYPE = "NEGOTIATE"
        self.rq = rq
        self.item_name = item_name
        self.max_price = max_price

    def __str__(self):
        return f"{self.TYPE} {self.rq} {self.item_name} {self.max_price}"


class Accept:
    def __init__(self, rq, item_name, max_price):
        self.TYPE = "ACCEPT"
        self.rq = rq
        self.item_name = item_name
        self.max_price = max_price

    def __str__(self):
        return f"{self.TYPE} {self.rq} {self.item_name} {self.max_price}"


class Refuse:
    def __init__(self, rq, item_name, max_price):
        self.TYPE = "REFUSE"
        self.rq = rq
        self.item_name = item_name
        self.max_price = max_price

    def __str__(self):
        return f"{self.TYPE} {self.rq} {self.item_name} {self.max_price}"


class Reserve:
    def __init__(self, rq, item_name, price):
        self.TYPE = "RESERVE"
        self.rq = rq
        self.item_name = item_name
        self.price = price

    def __str__(self):
        return f"{self.TYPE} {self.rq} {self.item_name} {self.price}"


class Cancel:
    def __init__(self, rq, item_name, price):
        self.TYPE = "CANCEL"
        self.rq = rq
        self.item_name = item_name
        self.price = price

    def __str__(self):
        return f"{self.TYPE} {self.rq} {self.item_name} {self.price}"


class Buy:
    def __init__(self, rq, item_name, price):
        self.TYPE = "BUY"
        self.rq = rq
        self.item_name = item_name
        self.price = price

    def __str__(self):
        return f"{self.TYPE} {self.rq} {self.item_name} {self.price}"
