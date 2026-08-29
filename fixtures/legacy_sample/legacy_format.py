def render_amount(v: float) -> str:
    if v < 0:
        raise ValueError("Value cannot be negative")
    amt = round(v, 2)
    return f"${amt:.2f}"
