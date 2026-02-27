"""
Скрипт для обработки XML-файлов мнемосхем.

1. Проходит по папкам шкафов в vision/LCSMnemo/
2. Сохраняет оригинальные XML в Modules/old_mnemo/<ШКАФ>/ (бэкап)
3. В каждом XML-файле заменяет пути вида objects/... на objects/objects_<ШКАФ>/...
4. Копирует соответствующие объекты из общей папки objects/ в objects/objects_<ШКАФ>/
5. Создаёт отчёт no_objects_found.txt со списком XML, где не найдено путей objects
"""

import re
import sys
import shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from report_utils import write_report
from parse_utils import read_text_safe, find_mnemo_dirs, PANELS_DIR, OBJECTS_DIR, LCSMEMO_DIR, REPORT_DIR, OLD_MNEMO_DIR

# Windows cp866/cp1251 ломает Unicode → форсируем UTF-8
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

REPORT_FILE = REPORT_DIR / "no_objects_found.txt"

# Паттерн: ищем пути вида objects/...(что-то)...xml
# Но НЕ уже заменённые (objects/objects_...)
PATTERN = re.compile(r'objects/(?!objects_)(.*?\.xml)')

# Паттерн для pathFS: /objects/PV/FPs/heatControl_SHD_03_1_P6  (без .xml, с ведущим /)
# WinCC OA автоматически добавляет .xml при открытии фейсплейта
PATTERN_PATHFS = re.compile(r'/objects/(?!objects_)([^"<>\s]+?)(?=</prop>|")')


def process_cabinet(cabinet_path: Path, no_objects_files: list[str]):
    """Обработка одной папки-шкафа."""
    cabinet_name = cabinet_path.name
    prefix = f"objects/objects_{cabinet_name}/"

    # Собираем уникальные относительные пути объектов для копирования
    objects_to_copy: set[str] = set()

    # Находим все XML-файлы в папке шкафа (рекурсивно)
    xml_files = list(cabinet_path.rglob("*.xml"))

    for xml_file in xml_files:
        text = read_text_safe(xml_file)
        if text is None:
            print(f"  [!] Не удалось прочитать: {xml_file}")
            continue

        # Ищем все вхождения objects/...xml
        matches = PATTERN.findall(text)

        # Ищем pathFS без .xml: /objects/PV/FPs/heatControl_...
        pathfs_matches = PATTERN_PATHFS.findall(text)

        if not matches and not pathfs_matches:
            no_objects_files.append(str(xml_file.relative_to(PANELS_DIR)))
            continue

        # Собираем пути объектов для копирования
        for match in matches:
            # match — это то, что после objects/, например PV/object/AI/AI.xml
            obj_rel_path = match  # например PV/object/AI/AI.xml
            objects_to_copy.add(obj_rel_path)

        # pathFS пути — добавляем .xml для копирования
        for match in pathfs_matches:
            obj_rel_path = match + ".xml"  # PV/FPs/heatControl_SHD_03_1_P6 → + .xml
            objects_to_copy.add(obj_rel_path)

        # Заменяем в тексте: стандартные пути с .xml
        new_text = PATTERN.sub(lambda m: f"objects/objects_{cabinet_name}/{m.group(1)}", text)
        # Заменяем pathFS: /objects/... → /objects/objects_<ШКАФ>/...
        new_text = PATTERN_PATHFS.sub(lambda m: f"/objects/objects_{cabinet_name}/{m.group(1)}", new_text)

        if new_text != text:
            # Сохраняем оригинал в Modules/old_mnemo/<ШКАФ>/
            rel = xml_file.relative_to(LCSMEMO_DIR)
            backup = OLD_MNEMO_DIR / rel
            if not backup.exists():
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(xml_file, backup)
                print(f"  [←] Бэкап: old_mnemo/{rel}")
            # Записываем изменённую версию
            xml_file.write_text(new_text, encoding="utf-8")
            print(f"  [✓] Обновлён: {xml_file.name}")

    # Копируем объекты
    copied_dirs: set[str] = set()
    for obj_rel in objects_to_copy:
        src = OBJECTS_DIR / obj_rel
        dst = OBJECTS_DIR / f"objects_{cabinet_name}" / obj_rel

        # Определяем папку объекта (последняя папка перед файлом)
        # Например для PV/object/AI/AI.xml — копируем всю структуру до файла
        src_file = src
        dst_file = dst

        if src_file.exists():
            # Определяем уникальную папку-объект чтобы не копировать дважды
            # Берём директорию файла как ключ уникальности
            obj_dir_key = str(Path(obj_rel).parent)
            if obj_dir_key in copied_dirs:
                continue
            copied_dirs.add(obj_dir_key)

            dst_file.parent.mkdir(parents=True, exist_ok=True)

            # Копируем всю папку объекта (все файлы в ней)
            src_obj_dir = src_file.parent
            dst_obj_dir = dst_file.parent

            if not dst_obj_dir.exists() or not any(dst_obj_dir.iterdir()):
                # Копируем содержимое папки объекта
                if src_obj_dir.is_dir():
                    shutil.copytree(src_obj_dir, dst_obj_dir, dirs_exist_ok=True)
                    print(f"  [→] Скопировано: {obj_dir_key}")
        else:
            print(f"  [?] Источник не найден: {src_file}")


def main():
    if not LCSMEMO_DIR.exists():
        print(f"Папка не найдена: {LCSMEMO_DIR}")
        return

    if not OBJECTS_DIR.exists():
        print(f"Папка objects не найдена: {OBJECTS_DIR}")
        print("Замена в XML будет выполнена, но копирование объектов пропущено.")

    no_objects_files: list[str] = []

    # Получаем список папок-шкафов (с учётом cabinets.txt)
    cabinets = find_mnemo_dirs()

    if not cabinets:
        print("Папки шкафов не найдены (проверьте cabinets.txt)")
        return

    print(f"Шкафов: {len(cabinets)}\n")

    for cabinet in cabinets:
        print(f"[Шкаф] {cabinet.name}")
        process_cabinet(cabinet, no_objects_files)
        print()

    # Записываем отчёт
    report_lines = []
    if no_objects_files:
        report_lines.append("XML-файлы, в которых не найдено путей objects:\n")
        for path in sorted(no_objects_files):
            report_lines.append(str(path))
    else:
        report_lines.append("Во всех XML-файлах были найдены пути objects.")
    write_report(REPORT_FILE, report_lines)

    print(f"Отчёт сохранён: {REPORT_FILE}")
    print(f"  XML без objects: {len(no_objects_files)}")


if __name__ == "__main__":
    main()
