"""
Подсчёт строк кода в двух проектах (Vue + Django).
Запускать из командной строки, передавая пути к проектам:
    python count_lines.py C:\путь\к\vue-проекту C:\путь\к\django-проекту
"""

import os
import sys
from pathlib import Path
from collections import defaultdict


# ---------- НАСТРОЙКИ ----------
# Папки, которые исключаем из поиска (регистронезависимо для Windows)
EXCLUDED_DIRS = {
    "node_modules", ".git", "__pycache__", "venv", ".venv", "env",
    ".env", "dist", "build", ".nuxt", ".output", "migrations",
    "staticfiles", "media", ".idea", ".vscode", ".pytest_cache",
    "coverage", "htmlcov",
}

# Расширения файлов Vue-проекта (фронтенд)
VUE_EXTENSIONS = {".vue", ".js", ".ts", ".jsx", ".tsx", ".css", ".scss", ".less", ".html", ".json"}

# Расширения файлов Django-проекта (бэкенд)
DJANGO_EXTENSIONS = {".py", ".html", ".css", ".js", ".json", ".yml", ".yaml", ".txt", ".md"}
# ---------------------------------


def count_lines_in_file(filepath: Path) -> tuple[int, int]:
    """
    Возвращает (всего_строк, логических_строк).
    Логические строки — без пустых и состоящих только из пробелов.
    """
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            total = len(lines)
            logical = sum(1 for line in lines if line.strip() != "")
            return total, logical
    except Exception:
        return 0, 0


def collect_files(root: Path, allowed_extensions: set) -> list[Path]:
    """Рекурсивно собирает файлы с нужными расширениями, исключая папки."""
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Исключаем ненужные папки
        dirnames[:] = [
            d for d in dirnames
            if d.lower() not in EXCLUDED_DIRS and not d.startswith(".")
        ]
        for filename in filenames:
            filepath = Path(dirpath) / filename
            if filepath.suffix.lower() in allowed_extensions:
                files.append(filepath)
    return files


def analyze_project(project_path: str, label: str, allowed_extensions: set) -> dict:
    """
    Анализирует один проект.
    Возвращает словарь с количеством файлов, общих строк и логических строк.
    """
    root = Path(project_path)
    if not root.exists():
        print(f"[ОШИБКА] Путь не найден: {project_path}")
        return {"files": 0, "total_lines": 0, "logical_lines": 0}

    print(f"\n{'='*60}")
    print(f"Сканирую: {label} -> {root}")
    print(f"{'='*60}")

    files = collect_files(root, allowed_extensions)
    stats_by_ext = defaultdict(lambda: {"files": 0, "total": 0, "logical": 0})
    grand_total = 0
    grand_logical = 0

    for f in sorted(files):
        total, logical = count_lines_in_file(f)
        ext = f.suffix.lower() or "без расширения"
        stats_by_ext[ext]["files"] += 1
        stats_by_ext[ext]["total"] += total
        stats_by_ext[ext]["logical"] += logical
        grand_total += total
        grand_logical += logical

    # Вывод по расширениям
    print(f"\n{'Расширение':<20} {'Файлов':>8} {'Всего строк':>12} {'Логических':>12}")
    print("-" * 54)
    for ext in sorted(stats_by_ext.keys()):
        s = stats_by_ext[ext]
        print(f"{ext:<20} {s['files']:>8} {s['total']:>12} {s['logical']:>12}")

    print("-" * 54)
    print(f"{'ИТОГО':<20} {len(files):>8} {grand_total:>12} {grand_logical:>12}")

    return {
        "files": len(files),
        "total_lines": grand_total,
        "logical_lines": grand_logical,
    }


def main():
    if len(sys.argv) < 3:
        print("Укажите пути к двум проектам:")
        print(f"  python {sys.argv[0]} <путь_к_vue> <путь_к_django>")
        print()
        print("Пример:")
        print(r'  python count_lines.py C:\Projects\frontend C:\Projects\backend')
        sys.exit(1)

    vue_path = sys.argv[1]
    django_path = sys.argv[2]

    stats_vue = analyze_project(vue_path, "Vue-проект", VUE_EXTENSIONS)
    stats_django = analyze_project(django_path, "Django-проект", DJANGO_EXTENSIONS)

    # ---------- ОБЩИЙ ИТОГ ----------
    total_files = stats_vue["files"] + stats_django["files"]
    total_all = stats_vue["total_lines"] + stats_django["total_lines"]
    total_logical = stats_vue["logical_lines"] + stats_django["logical_lines"]

    print(f"\n{'='*60}")
    print("ОБЩИЙ ОБЪЁМ ПРОГРАММНОГО ПРОДУКТА")
    print(f"{'='*60}")
    print(f"  Всего файлов:                  {total_files:>6}")
    print(f"  Всего строк (физических):      {total_all:>6}")
    print(f"  Всего строк (логических):      {total_logical:>6}")
    print(f"{'='*60}")

    # Готовая фраза для вставки в ВКР
    print("\n--- Фраза для вывода в ВКР ---")
    print(f"Общий объём программного продукта составляет {total_all} физических строк "
          f"({total_logical} логических строк, без учёта пустых и комментариев). "
          f"Фронтенд (Vue) — {stats_vue['total_lines']} строк, "
          f"бэкенд (Django) — {stats_django['total_lines']} строк.")


if __name__ == "__main__":
    main()