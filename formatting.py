# utils/formatting.py
# Функции форматирования чисел и времени.

def format_number(num: int) -> str:
    """Форматирует целое число с разделителями тысяч (пробелами)."""
    return f"{num:,}".replace(",", " ")


def format_duration(minutes: int) -> str:
    """Преобразует минуты в человекочитаемую строку."""
    hours = minutes // 60
    mins = minutes % 60
    parts = []
    if hours:
        parts.append(f"{hours} ч")
    if mins:
        parts.append(f"{mins} мин")
    return " ".join(parts) if parts else "0 мин"