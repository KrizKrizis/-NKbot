# fbot.py
# Скрипт для пересоздания только папки admin.
# Все остальные папки и файлы проекта не затрагиваются.

import os
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ADMIN_DIR = os.path.join(BASE_DIR, "admin")


def remove_folder(path):
    """Удаляет папку со всем содержимым."""
    if os.path.exists(path):
        shutil.rmtree(path)


def create_file(path, content=""):
    """Создаёт файл с заданным содержимым (по умолчанию пустой)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def create_package(path):
    """Создаёт папку и файл __init__.py внутри."""
    os.makedirs(path, exist_ok=True)
    create_file(os.path.join(path, "__init__.py"))


def recreate_admin():
    """Удаляет старую папку admin и создаёт новую структуру."""
    remove_folder(ADMIN_DIR)

    # Корневой __init__.py
    create_package(ADMIN_DIR)

    # Файлы в корне admin
    root_files = [
        "base.py",
        "player_management.py",
        "team_management.py",
        "project_management.py",
        "system_management.py",
        "complaint_management.py",
        "test_panel_management.py",
    ]
    for filename in root_files:
        create_file(os.path.join(ADMIN_DIR, filename))

    # Категории и их подпапки
    categories = {
        "helpers": {
            "handlers": ["helpers.py"],
            "keyboards": ["helpers_menu.py"],
        },
        "administration": {
            "handlers": ["administration.py", "players.py", "complaints.py", "team.py", "statistics.py"],
            "keyboards": [
                "administration_menu.py",
                "players_keyboards.py",
                "complaints_keyboards.py",
                "team_keyboards.py",
            ],
        },
        "spec_administration": {
            "handlers": ["spec_admin.py", "curator.py", "tester.py", "deputy_founder.py"],
            "keyboards": [
                "spec_admin_menu.py",
                "curator_keyboards.py",
                "tester_keyboards.py",
                "deputy_keyboards.py",
            ],
        },
        "project_leadership": {
            "handlers": ["founder.py", "system.py", "players.py", "team.py", "project.py", "roles.py"],
            "keyboards": [
                "leadership_menu.py",
                "players_keyboards.py",
                "team_keyboards.py",
                "project_keyboards.py",
                "system_keyboards.py",
                "roles_keyboards.py",
            ],
        },
    }

    for category, sub in categories.items():
        cat_path = os.path.join(ADMIN_DIR, category)
        create_package(cat_path)

        # handlers
        handlers_dir = os.path.join(cat_path, "handlers")
        create_package(handlers_dir)
        for hf in sub["handlers"]:
            create_file(os.path.join(handlers_dir, hf))

        # keyboards
        keyboards_dir = os.path.join(cat_path, "keyboards")
        create_package(keyboards_dir)
        for kf in sub["keyboards"]:
            create_file(os.path.join(keyboards_dir, kf))


if __name__ == "__main__":
    print("Пересоздание папки admin...")
    recreate_admin()
    print("Готово: папка admin обновлена, остальные файлы не тронуты.")