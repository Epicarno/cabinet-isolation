"""
Замена ссылок на скрипты в XML объектах (v2).

ВСЕ варианты заменяются на единый формат с .ctl:
  PNR_Ventcontent.ctl     → Ventcontent_<ШКАФ>.ctl
  PNR_Ventcontent         → Ventcontent_<ШКАФ>.ctl  (добавляет .ctl!)
  Denostration_Ventcontent.ctl → Ventcontent_<ШКАФ>.ctl
  Denostration_Ventcontent     → Ventcontent_<ШКАФ>.ctl  (добавляет .ctl!)

После замены удаляет дублирующиеся #uses строки.

Результат: replace_scripts_report.txt
"""

import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from report_utils import write_report
from parse_utils import read_text_safe, find_cabinet_dirs, PANELS_DIR, OBJECTS_DIR, REPORT_DIR

# Windows cp866/cp1251 ломает Unicode → форсируем UTF-8
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

REPORT_FILE = REPORT_DIR / "replace_scripts_report.txt"

# Замены: (что ищем, на что меняем) — порядок важен: .ctl сначала!
REPLACEMENTS = [
    ("PNR_Ventcontent.ctl", "{NEW}.ctl"),
    ("Denostration_Ventcontent.ctl", "{NEW}.ctl"),
    ("PNR_Ventcontent", "{NEW}.ctl"),           # без .ctl → добавляем .ctl
    ("Denostration_Ventcontent", "{NEW}.ctl"),   # без .ctl → добавляем .ctl
]


def dedup_uses(text: str, new_name_ctl: str) -> tuple[str, int]:
    """
    Удаляет дублирующиеся #uses строки с new_name_ctl.
    Ищет полные конструкции #uses в двух форматах:
    - #uses \"objLogic/NAME\"    (escaped)
    - #uses &quot;objLogic/NAME&quot;  (XML entities)

    Оставляет первое вхождение, удаляет остальные (целые строки).
    """
    removed = 0

    uses_variants = [
        f'#uses \\"objLogic/{new_name_ctl}\\"',
        f'#uses &quot;objLogic/{new_name_ctl}&quot;',
    ]

    for uses_str in uses_variants:
        first = text.find(uses_str)
        if first == -1:
            continue

        # Ищем все последующие вхождения
        pos = text.find(uses_str, first + len(uses_str))
        while pos != -1:
            # Расширяем до целой строки: от начала строки до \n
            line_start = pos
            while line_start > 0 and text[line_start - 1] != '\n':
                line_start -= 1

            line_end = pos + len(uses_str)
            while line_end < len(text) and text[line_end] in ' \t\r':
                line_end += 1
            if line_end < len(text) and text[line_end] == '\n':
                line_end += 1

            text = text[:line_start] + text[line_end:]
            removed += 1

            # Ищем следующее вхождение от той же позиции
            pos = text.find(uses_str, line_start)

    return text, removed


def process_file(xml_file: Path, cabinet_name: str) -> tuple[bool, int, int, str]:
    """
    Обрабатывает один файл.
    Возвращает (изменён, замен, дублей_удалено, детали).
    """
    text = read_text_safe(xml_file)
    if text is None:
        return False, 0, 0, ""

    # Проверяем есть ли что менять
    if "PNR_Ventcontent" not in text and "Denostration_Ventcontent" not in text:
        return False, 0, 0, ""

    had_pnr = "PNR_Ventcontent" in text
    had_demo = "Denostration_Ventcontent" in text

    new_name_ctl = f"Ventcontent_{cabinet_name}.ctl"
    total_count = 0

    # Замены в правильном порядке (.ctl сначала, чтобы не ловить подстроки)
    for old, new_template in REPLACEMENTS:
        new = new_template.replace("{NEW}", f"Ventcontent_{cabinet_name}")
        count = text.count(old)
        if count > 0:
            text = text.replace(old, new)
            total_count += count

    # Дедупликация #uses
    text, dups = dedup_uses(text, new_name_ctl)

    xml_file.write_text(text, encoding="utf-8")

    if had_pnr and had_demo:
        detail = "PNR + Demo → один скрипт"
    elif had_pnr:
        detail = "PNR → заменён"
    else:
        detail = "Demo → заменён"

    if dups:
        detail += f" (дублей: {dups})"

    return True, total_count, dups, detail


def main():
    if not OBJECTS_DIR.exists():
        print(f"Папка не найдена: {OBJECTS_DIR}")
        return

    cabinet_dirs = find_cabinet_dirs(OBJECTS_DIR)

    if not cabinet_dirs:
        print("Папки objects/objects_<ШКАФ>/ не найдены.")
        return

    report: list[str] = []
    report.append("Отчёт: замена PNR/Denostration_Ventcontent → Ventcontent_<ШКАФ>.ctl (v2)")
    report.append("=" * 70)
    report.append("Все варианты нормализуются к единому формату с .ctl")
    report.append("")

    total_files = 0
    total_replacements = 0
    total_dups = 0

    for cab_dir in cabinet_dirs:
        cabinet_name = cab_dir.name.replace("objects_", "", 1)
        cab_files = 0
        cab_report: list[str] = []

        for xml_file in sorted(cab_dir.rglob("*.xml")):
            changed, count, dups, detail = process_file(xml_file, cabinet_name)
            if changed:
                file_rel = str(xml_file.relative_to(PANELS_DIR)).replace("\\", "/")
                cab_report.append(f"    [✓] {file_rel}  — {detail}")
                cab_files += 1
                total_replacements += count
                total_dups += dups

        if cab_files:
            report.append(f"[{cabinet_name}] файлов: {cab_files}")
            report.extend(cab_report)
            report.append("")

        total_files += cab_files
        if cab_files:
            print(f"  [{cabinet_name}] {cab_files} файлов")

    report.append("=" * 70)
    report.append(f"Файлов: {total_files}")
    report.append(f"Замен: {total_replacements}")
    report.append(f"Дублей удалено: {total_dups}")

    write_report(REPORT_FILE, report)

    print(f"\nФайлов: {total_files}, замен: {total_replacements}, дублей: {total_dups}")
    print(f"Отчёт: {REPORT_FILE}")


if __name__ == "__main__":
    main()
