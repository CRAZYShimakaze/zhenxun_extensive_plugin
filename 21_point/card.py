class Card:
    symbols = ["♥", "♦", "♣", "♠"]
    value_str = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]

    def __init__(self, num):
        self.num = num
        self.value = self.get_value()
        self.symbol = self.symbols[num // 13]

    def get_value(self):
        return self.num % 13 + 1

    def __str__(self):
        return self.symbol + self.value_str[self.value - 1]
