import payments


def create_order(item_id: str, amount: float) -> str:
    receipt = payments.charge(amount)
    return f"ORDER-{item_id}-{receipt}"


def cancel_order(order_id: str) -> bool:
    print(f"Cancelling order {order_id}")
    return True
