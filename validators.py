# utils/validators.py
# Функции валидации ввода.

def is_valid_number(text: str) -> bool:
    """Проверяет, является ли строка положительным целым числом."""
    return text.isdigit() and int(text) >= 0


def is_valid_id(text: str) -> bool:
    """Проверяет, является ли строка числовым ID."""
    return text.isdigit()