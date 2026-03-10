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

from report_utils import write_report
from parse_utils import (
    read_text_safe, strip_comments, find_mnemo_dirs,
    PANELS_DIR, OBJECTS_DIR, LCSMEMO_DIR, REPORT_DIR, OLD_MNEMO_DIR,
)

# Windows cp866/cp1251 ломает Unicode → форсируем UTF-8
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

REPORT_FILE = REPORT_DIR / "no_objects_found.txt"

# Паттерн: ищем пути вида objects/...(что-то)...xml
# Но НЕ уже заменённые (objects/objects_...)
PATTERN = re.compile(r'objects/(?!objects_)(.*?\.xml)')

# Паттерн для pathFS: /objects/PV/FPs/heatControl_SHD_03_1_P6  (без .xml)
# Ведущий / опционален — в данных встречаются оба варианта
# WinCC OA автоматически добавляет .xml при открытии фейсплейта
PATTERN_PATHFS = re.compile(r'/?objects/(?!objects_)([^"<>\s\\]+?)(?=</prop>|")')

# Уже изолированные ссылки — только для копирования (не для переписывания)
# objects/objects_<ШКАФ>/PV/FPs/heatControl.xml
PATTERN_ALREADY = re.compile(r'objects/objects_([^/]+)/(.*?\.xml)')
# pathFS уже изолированный: /objects/objects_<ШКАФ>/PV/FPs/heatControl (/ опционален)
PATTERN_ALREADY_PATHFS = re.compile(r'/?objects/objects_([^/]+)/([^"<>\s\\]+?)(?=</prop>|")')


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

        # Ищем все вхождения objects/...xml (ещё не изолированные)
        matches = PATTERN.findall(text)

        # Ищем pathFS без .xml: /objects/PV/FPs/heatControl_...
        pathfs_matches = PATTERN_PATHFS.findall(text)

        # Ищем уже изолированные ссылки — только для копирования
        already_matches = PATTERN_ALREADY.findall(text)      # [(шкаф, rel_path)]
        already_pathfs  = PATTERN_ALREADY_PATHFS.findall(text)

        if not matches and not pathfs_matches and not already_matches and not already_pathfs:
            no_objects_files.append(str(xml_file.relative_to(PANELS_DIR)))
            continue

        # Собираем пути объектов для копирования
        for match in matches:
            objects_to_copy.add(match)

        # pathFS пути — нормализуем: если уже .xml, не дублируем
        for match in pathfs_matches:
            obj_rel_path = match if match.endswith(".xml") else match + ".xml"
            objects_to_copy.add(obj_rel_path)

        # Уже изолированные — собираем только если шкаф совпадает
        for cab, rel_path in already_matches:
            if cab == cabinet_name:
                objects_to_copy.add(rel_path)

        for cab, rel_path in already_pathfs:
            if cab == cabinet_name:
                obj_rel = rel_path if rel_path.endswith(".xml") else rel_path + ".xml"
                objects_to_copy.add(obj_rel)

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

    # --- Копируем объекты и итеративно дособираем перекрёстные ссылки ---
    cabinet_obj_dir = OBJECTS_DIR / f"objects_{cabinet_name}"
    copied: set[str] = set()          # уже скопированные
    to_scan: set[str] = set(objects_to_copy)  # очередь на сканирование

    iteration = 0
    while to_scan:
        iteration += 1
        if iteration > 50:
            print(f"  [!] Прервано: >50 итераций перекрёстных ссылок")
            break

        # Копируем все файлы из текущей очереди
        newly_copied: list[Path] = []
        for obj_rel in sorted(to_scan):
            if obj_rel in copied:
                continue
            copied.add(obj_rel)

            src = OBJECTS_DIR / obj_rel
            dst = cabinet_obj_dir / obj_rel

            if src.exists():
                if not dst.exists():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
                    print(f"  [→] Скопирован: {obj_rel}")
                newly_copied.append(dst)
            else:
                print(f"  [?] Источник не найден: {src}")

        # Сканируем только что скопированные объекты на перекрёстные ссылки
        to_scan = set()
        for dst_file in newly_copied:
            text = read_text_safe(dst_file)
            if text is None:
                continue
            clean = strip_comments(text)

            for m in PATTERN.finditer(clean):
                ref = m.group(1)
                if ref not in copied:
                    to_scan.add(ref)

            for m in PATTERN_PATHFS.finditer(clean):
                raw = m.group(1)
                ref = raw if raw.endswith(".xml") else raw + ".xml"
                if ref not in copied:
                    to_scan.add(ref)

            # Уже изолированные перекрёстные ссылки (objects_<шкаф>/...)
            for m in PATTERN_ALREADY.finditer(clean):
                cab, rel = m.group(1), m.group(2)
                if cab == cabinet_name and rel not in copied:
                    to_scan.add(rel)

            for m in PATTERN_ALREADY_PATHFS.finditer(clean):
                cab, raw = m.group(1), m.group(2)
                if cab == cabinet_name:
                    ref = raw if raw.endswith(".xml") else raw + ".xml"
                    if ref not in copied:
                        to_scan.add(ref)

        if to_scan:
            print(f"  [↻] Найдено перекрёстных ссылок: {len(to_scan)} (итерация {iteration})")


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
