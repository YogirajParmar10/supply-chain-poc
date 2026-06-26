def format_id(prefix: str, number: int, width: int) -> str:
    return f"{prefix}{number:0{width}d}"
