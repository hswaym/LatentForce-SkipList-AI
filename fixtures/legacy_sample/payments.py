import formatting


def charge(amount: float) -> str:
    formatted = formatting.format_amount(amount)
    return f"TXN-CHARGED-{formatted}"


def deprecated_refund(transaction_id: str, amount: float) -> bool:
    print(f"Refunding transaction {transaction_id} for amount {amount}")
    return True
