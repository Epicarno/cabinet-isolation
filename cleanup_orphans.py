"""
Скрипт для поиска и очистки лишних файлов в objects/objects_<ШКАФ>/.

Проблема: copytree копировал целые папки, а не отдельные файлы,
поэтому в шкаф попали объекты от других шкафов.

Логика:
1. Для каждого шкафа собирает ВСЕ ссылки из:
   - XML мнемосхем в vision/LCSMnemo/<ШКАФ>/
   - XML объектов в objects/objects_<ШКАФ>/ (перекрёстные)
2. Файлы в objects/objects_<ШКАФ>/, на которые никто не ссылается — лишние
3. Создаёт отчёт и по желанию удаляет лишние файлы

Результат: orphan_files_report.txt
"""

import re
import os
import sys
from pathlib import Path
from report_utils import write_report
from parse_utils import read_text_safe, find_cabinet_dirs, OBJECTS_DIR, LCSMEMO_DIR, REPORT_DIR

REPORT_FILE = REPORT_DIR / "orphan_files_report.txt"

# Ссылки вида objects/objects_<ШКАФ>/...xml
PATTERN_FULL = re.compile(r'objects/objects_[^/]+/(.*?\.xml)')
# Ссылки вида objects/...xml (старый формат, если остались)
PATTERN_OLD = re.compile(r'objects/(?!objects_)(.*?\.xml)')


def collect_referenced_files(cabinet_name: str, cabinet_obj_dir: Path) -> set[str]:
    """
    Собирает все файлы, на которые есть ссылки для данного шкафа.
    Возвращает set относительных путей внутри objects_<ШКАФ>/ (например PV/FPs/heatControl_SHD_03_1.xml)
    """
    referenced: set[str] = set()
    obj_prefix = f"objects_{cabinet_name}"

    # 1. Ссылки из мнемосхем шкафа (vision/LCSMnemo/<ШКАФ>/)
    mnemo_dir = LCSMEMO_DIR / cabinet_name
    if mnemo_dir.exists():
        for xml_file in mnemo_dir.rglob("*.xml"):
            text = read_text_safe(xml_file)
            if text is None:
                continue

            # Ищем ссылки на objects/objects_<ЭТОТ_ШКАФ>/...
            for m in PATTERN_FULL.finditer(text):
                full_match = m.group(0)
                if f"objects/{obj_prefix}/" in full_match:
                    referenced.add(m.group(1))

            # На случай если остались старые ссылки
            for m in PATTERN_OLD.finditer(text):
                referenced.add(m.group(1))

    # 2. Ссылки из самих объектов шкафа (перекрёстные)
    #    Итеративно — объект A ссылается на B, B на C и т.д.
    prev_size = -1
    iteration = 0
    while len(referenced) != prev_size:
        prev_size = len(referenced)
        iteration += 1
        if iteration > 50:
            break

        for obj_rel in list(referenced):
            obj_file = cabinet_obj_dir / obj_rel
            if not obj_file.exists():
                continue
            text = read_text_safe(obj_file)
            if text is None:
                continue

            for m in PATTERN_FULL.finditer(text):
                full_match = m.group(0)
                if f"objects/{obj_prefix}/" in full_match:
                    referenced.add(m.group(1))

            for m in PATTERN_OLD.finditer(text):
                referenced.add(m.group(1))

    return referenced


def main():
    # Режим из аргументов командной строки или интерактивно
    if len(sys.argv) > 1 and sys.argv[1] == "2":
        delete_mode = True
    elif len(sys.argv) > 1 and sys.argv[1] == "1":
        delete_mode = False
    else:
        print("Режимы работы:")
        print("  1 - Только отчёт (ничего не удаляет)")
        print("  2 - Отчёт + удаление лишних файлов")
        print()
        mode = input("Выберите режим (1/2): ").strip()
        delete_mode = mode == "2"

    if delete_mode and len(sys.argv) <= 1:
        confirm = input("Вы уверены? Лишние файлы будут УДАЛЕНЫ (y/n): ").strip().lower()
        if confirm != "y":
            print("Отменено.")
            return

    # Находим папки шкафов
    cabinet_obj_dirs = find_cabinet_dirs(OBJECTS_DIR)

    if not cabinet_obj_dirs:
        print("Папки objects/objects_<ШКАФ>/ не найдены.")
        return

    report_lines: list[str] = []
    report_lines.append("Отчёт по лишним файлам в objects/objects_<ШКАФ>/")
    report_lines.append("=" * 60)
    report_lines.append("")

    total_orphans = 0
    total_deleted = 0

    for cab_obj_dir in cabinet_obj_dirs:
        cabinet_name = cab_obj_dir.name.replace("objects_", "")
        print(f"\n[Шкаф] {cabinet_name}")

        # Все файлы в папке шкафа (не только XML)
        all_files = sorted(f for f in cab_obj_dir.rglob("*") if f.is_file())
        all_rels = set()
        for f in all_files:
            all_rels.add(str(f.relative_to(cab_obj_dir)).replace("\\", "/"))

        # Собираем ссылки (только XML реально ссылаются)
        referenced = collect_referenced_files(cabinet_name, cab_obj_dir)

        # Лишние = есть в папке, но нет в ссылках
        orphans = sorted(all_rels - referenced)

        report_lines.append(f"[{cabinet_name}]")
        report_lines.append(f"  Всего файлов в папке: {len(all_rels)}")
        report_lines.append(f"  Используемых:         {len(all_rels) - len(orphans)}")
        report_lines.append(f"  Лишних:               {len(orphans)}")

        if orphans:
            report_lines.append(f"  Лишние файлы:")
            for orph in orphans:
                full_path = cab_obj_dir / orph
                report_lines.append(f"    ✗ {orph}")

                if delete_mode and full_path.exists():
                    full_path.unlink()
                    total_deleted += 1

            total_orphans += len(orphans)
            print(f"  Лишних: {len(orphans)}")
            if delete_mode:
                print(f"  Удалено: {len(orphans)}")
        else:
            print(f"  Всё чисто!")

        report_lines.append("")

    # Удаляем пустые папки после очистки
    if delete_mode:
        for cab_obj_dir in cabinet_obj_dirs:
            for dirpath, dirnames, filenames in os.walk(cab_obj_dir, topdown=False):
                if not os.listdir(dirpath):
                    os.rmdir(dirpath)

    # Итого
    report_lines.append("=" * 60)
    report_lines.append("ИТОГО:")
    report_lines.append(f"  Всего лишних файлов: {total_orphans}")
    if delete_mode:
        report_lines.append(f"  Удалено: {total_deleted}")

    write_report(REPORT_FILE, report_lines)

    print(f"\nОтчёт: {REPORT_FILE}")
    print(f"Лишних файлов найдено: {total_orphans}")
    if delete_mode:
        print(f"Удалено: {total_deleted}")


if __name__ == "__main__":
    main()
