from utils import ActiveClass

def calculate_discount_v1(price, factor):
    res = price * (1 - factor)
    res = max(0, res)
    return round(res, 2)

def calculate_discount_v2(amount, pct):
    res = amount * (1 - pct)
    res = max(0, res)
    return round(res, 2)

def main():
    obj = ActiveClass()
    print(obj.process())
    print(calculate_discount_v1(100, 0.1))

if __name__ == "__main__":
    main()
