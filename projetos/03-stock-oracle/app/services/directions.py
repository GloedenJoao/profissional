def direction_from_prices(base_price: float, comparison_price: float, tolerance_pct: float = 0.001) -> str:
    if base_price <= 0 or comparison_price <= 0:
        raise ValueError("prices must be positive")
    change = (comparison_price - base_price) / base_price
    if change > tolerance_pct:
        return "up"
    if change < -tolerance_pct:
        return "down"
    return "flat"

