"""
Скрипт для обработки перекрёстных ссылок внутри объектов.

Проходит по папкам objects/objects_<ШКАФ>/ и:
1. Находит в XML ссылки вида objects/...xml (ещё не заменённые)
2. Заменяет их на objects/objects_<ШКАФ>/...xml
3. Копирует недостающие объекты из общей папки objects/
4. Повторяет, пока все ссылки не обработаны (новые объекты тоже могут ссылаться)

Результат: cross_refs_fix_report.txt
"""

import re
import shutil
from pathlib import Path
from report_utils import write_report
from parse_utils import read_text_safe, find_cabinet_dirs, PANELS_DIR, OBJECTS_DIR, REPORT_DIR

REPORT_FILE = REPORT_DIR / "cross_refs_fix_report.txt"

# Ищем objects/...xml, но НЕ уже заменённые objects/objects_...
PATTERN = re.compile(r'objects/(?!objects_)(.*?\.xml)')


def process_cabinet(cabinet_dir: Path, report_lines: list[str]) -> dict:
    """Обрабатывает одну папку-шкаф. Возвращает статистику."""
    cabinet_name = cabinet_dir.name  # objects_SHD_7
    # missing: dict {недостающий_объект -> set(файлы_где_ссылка)}
    stats = {"files_updated": 0, "refs_replaced": 0, "objects_copied": 0, "missing": {}}

    # Итеративно обрабатываем, пока есть что менять
    # (новые скопированные объекты тоже могут содержать ссылки)
    iteration = 0
    while True:
        iteration += 1
        found_new = False
        # obj_rel_path -> set(файлы, где встречается ссылка)
        objects_to_copy: dict[str, set[str]] = {}

        xml_files = sorted(cabinet_dir.rglob("*.xml"))

        for xml_file in xml_files:
            text = read_text_safe(xml_file)
            if text is None:
                continue

            matches = PATTERN.findall(text)
            if not matches:
                continue

            file_rel = str(xml_file.relative_to(PANELS_DIR))

            # Собираем объекты для копирования с привязкой к файлу-источнику
            for match in matches:
                if match not in objects_to_copy:
                    objects_to_copy[match] = set()
                objects_to_copy[match].add(file_rel)

            # Заменяем пути
            new_text = PATTERN.sub(
                lambda m: f"objects/{cabinet_name}/{m.group(1)}",
                text
            )

            if new_text != text:
                xml_file.write_text(new_text, encoding="utf-8")
                replacements = len(matches)
                stats["files_updated"] += 1
                stats["refs_replaced"] += replacements
                found_new = True

        # Копируем недостающие объекты
        copied_dirs: set[str] = set()
        for obj_rel, referencing_files in objects_to_copy.items():
            src = OBJECTS_DIR / obj_rel
            dst = cabinet_dir / obj_rel

            obj_dir_key = str(Path(obj_rel).parent)
            if obj_dir_key in copied_dirs:
                continue
            copied_dirs.add(obj_dir_key)

            if dst.exists():
                # Уже есть — не копируем
                continue

            if src.exists():
                src_obj_dir = src.parent
                dst_obj_dir = dst.parent
                dst_obj_dir.mkdir(parents=True, exist_ok=True)
                if src_obj_dir.is_dir():
                    shutil.copytree(src_obj_dir, dst_obj_dir, dirs_exist_ok=True)
                    stats["objects_copied"] += 1
                    found_new = True  # новые файлы — нужен ещё проход
            else:
                missing_key = f"objects/{obj_rel}"
                if missing_key not in stats["missing"]:
                    stats["missing"][missing_key] = set()
                stats["missing"][missing_key].update(referencing_files)

        if not found_new:
            break

        # Защита от бесконечного цикла
        if iteration > 50:
            report_lines.append(f"  [!] Прервано: слишком много итераций ({iteration})")
            break

    return stats


def main():
    cabinet_dirs = find_cabinet_dirs(OBJECTS_DIR)

    if not cabinet_dirs:
        print("Папки objects/objects_<ШКАФ>/ не найдены.")
        print("Сначала запустите основной скрипт process_mnemo.py")
        return

    print(f"Найдено папок-шкафов: {len(cabinet_dirs)}\n")

    report_lines: list[str] = []
    report_lines.append("Отчёт по обработке перекрёстных ссылок в объектах")
    report_lines.append("=" * 60)
    report_lines.append("")

    total_files = 0
    total_refs = 0
    total_copied = 0
    total_missing: dict[str, set[str]] = {}

    for cab_dir in cabinet_dirs:
        cabinet_label = cab_dir.name.replace("objects_", "")
        print(f"[Шкаф] {cabinet_label}")

        stats = process_cabinet(cab_dir, report_lines)

        total_files += stats["files_updated"]
        total_refs += stats["refs_replaced"]
        total_copied += stats["objects_copied"]

        report_lines.append(f"[{cabinet_label}]")
        report_lines.append(f"  Файлов обновлено: {stats['files_updated']}")
        report_lines.append(f"  Ссылок заменено:  {stats['refs_replaced']}")
        report_lines.append(f"  Объектов скопировано: {stats['objects_copied']}")

        if stats["missing"]:
            report_lines.append(f"  Не найдено в sources:")
            for m, refs in sorted(stats["missing"].items()):
                report_lines.append(f"    ✗ {m}")
                report_lines.append(f"      Ссылается из:")
                for ref in sorted(refs):
                    report_lines.append(f"        ← {ref}")
                if m not in total_missing:
                    total_missing[m] = set()
                total_missing[m].update(refs)

        report_lines.append("")

        print(f"  Обновлено: {stats['files_updated']} файлов, "
              f"{stats['refs_replaced']} ссылок, "
              f"{stats['objects_copied']} скопировано")
        if stats["missing"]:
            print(f"  Не найдено: {len(stats['missing'])}")
        print()

    # Итого
    report_lines.append("=" * 60)
    report_lines.append("ИТОГО:")
    report_lines.append(f"  Файлов обновлено:    {total_files}")
    report_lines.append(f"  Ссылок заменено:     {total_refs}")
    report_lines.append(f"  Объектов скопировано: {total_copied}")
    if total_missing:
        report_lines.append(f"  Объектов не найдено: {len(total_missing)}")
        for m in sorted(total_missing.keys()):
            report_lines.append(f"    ✗ {m}")
            report_lines.append(f"      Ссылается из:")
            for ref in sorted(total_missing[m]):
                report_lines.append(f"        ← {ref}")

    write_report(REPORT_FILE, report_lines)

    print(f"Отчёт: {REPORT_FILE}")
    if not total_refs:
        print("Перекрёстных ссылок не найдено — всё уже чисто!")


if __name__ == "__main__":
    main()
