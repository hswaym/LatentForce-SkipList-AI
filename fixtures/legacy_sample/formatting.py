def format_amount(value: float) -> str:
    if value < 0:
        raise ValueError("Value cannot be negative")
    rounded = round(value, 2)
    return f"${rounded:.2f}"
