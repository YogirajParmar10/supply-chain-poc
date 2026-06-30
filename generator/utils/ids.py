import re


def format_id(prefix: str, number: int, width: int) -> str:
    return f"{prefix}{number:0{width}d}"


def parse_prefixed_id(value: str, prefix: str) -> int | None:
    match = re.match(rf"^{re.escape(prefix)}(\d+)$", value.strip())
    if not match:
        return None
    return int(match.group(1))


def next_id_start(existing_ids: list[str], prefix: str) -> int:
    max_number = 0
    for value in existing_ids:
        if value is None:
            continue
        parsed = parse_prefixed_id(str(value), prefix)
        if parsed is not None:
            max_number = max(max_number, parsed)
    return max_number + 1

