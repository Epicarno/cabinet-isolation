"""
Общий модуль для записи отчётов.

Все скрипты пайплайна импортируют:
    from report_utils import write_report

Использование:
    python3 split_ctl.py           # перезаписывает отчёт
    python3 split_ctl.py --append  # добавляет в конец с таймстампом
"""

import sys
from datetime import datetime
from pathlib import Path


def write_report(filepath: Path | str, lines: list[str]):
    """
    Записывает отчёт в файл.
    Без --append: перезаписывает файл.
    С --append: добавляет в конец с разделителем и таймстампом.
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(lines) + "\n"
    append_mode = "--append" in sys.argv

    if append_mode:
        sep = "\n" + "━" * 70 + "\n"
        sep += f"▶ Запуск: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        sep += "━" * 70 + "\n\n"
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(sep + content)
    else:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
