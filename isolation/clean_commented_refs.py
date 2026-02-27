#!/usr/bin/env python3
"""
clean_commented_refs.py — Удаление закомментированных ссылок на фейсплейты
                          и файлов-сирот, которые из-за них выживали.

Проблема:
  cleanup_orphans.py ищет ссылки grep'ом по всему тексту XML.
  Закомментированные строки вида:
    //  ChildPanelOnRelativ("objects/objects_SHD_03_1/PV/FPs/xxx.xml", ...)
  считаются реальными ссылками, и файл xxx.xml не удаляется.

Логика:
  1. Для каждого шкафа находит все XML в objects_<ШКАФ>/
  2. Собирает "активные" ссылки (не в комментариях) из мнемосхем + объектов
  3. Собирает "комментарийные" ссылки (строки начинающиеся с //)
  4. Файлы, на которые есть ТОЛЬКО комментарийные ссылки → comment orphans
  5. Удаляет закомментированные строки со ссылками + файлы-сироты

Режимы:
  --dry-run  (по умолчанию) — только отчёт
  --apply                  — удалить файлы и почистить комментарии

Использование:
  python clean_commented_refs.py                  # dry-run все шкафы
  python clean_commented_refs.py --apply SHD_03_1 # применить к SHD_03_1
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from collections import defaultdict

# Windows cp1251 ломает Unicode → форсируем UTF-8
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

SCRIPT_DIR  = Path(__file__).resolve().parent
MODULES_DIR = SCRIPT_DIR.parent
REPORT_DIR  = MODULES_DIR / "reports"

VENT_DIR   = MODULES_DIR / "ventcontent"
OBJECTS_DIR = VENT_DIR / "panels" / "objects"
MNEMO_DIR   = VENT_DIR / "panels" / "vision" / "LCSMnemo"

sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from parse_utils import read_text_safe, load_active_cabinets

# Паттерн ссылки на XML-файл внутри objects_<ШКАФ>/
REF_RE = re.compile(r'objects/objects_[A-Za-z0-9_]+/([\S]*?\.xml)')

# Паттерны комментариев
SINGLE_LINE_COMMENT = re.compile(r'^\s*//')
BLOCK_COMMENT_START = re.compile(r'/\*')
BLOCK_COMMENT_END   = re.compile(r'\*/')


def is_line_commented(line: str) -> bool:
    """Проверяет — начинается ли строка с // (однострочный комментарий)."""
    stripped = line.lstrip()
    return stripped.startswith("//")


def classify_refs_in_file(filepath: Path, obj_prefix: str
                          ) -> tuple[set[str], dict[str, list[tuple[int, str]]]]:
    """Анализирует XML-файл: разделяет ссылки на активные и закомментированные.

    Returns:
        active_refs     — set относительных путей (внутри objects_<ШКАФ>/)
        commented_refs  — {rel_path: [(line_no, line_text), ...]}
    """
    text = read_text_safe(filepath)
    if not text:
        return set(), {}

    active: set[str] = set()
    commented: dict[str, list[tuple[int, str]]] = defaultdict(list)

    in_block_comment = False

    for line_no, line in enumerate(text.splitlines(), 1):
        # Трекинг блочных комментариев /* ... */
        if in_block_comment:
            if BLOCK_COMMENT_END.search(line):
                in_block_comment = False
                # Всё до */ — ещё комментарий, после — код
                # Для простоты считаем всю строку комментарием
            for m in REF_RE.finditer(line):
                full = m.group(0)
                if f"objects/{obj_prefix}/" in full:
                    commented[m.group(1)].append((line_no, line.rstrip()))
            continue

        if BLOCK_COMMENT_START.search(line) and not BLOCK_COMMENT_END.search(line):
            # Начало блочного комментария
            # Ссылки до /* — активные, после — комментарийные
            # Для простоты: если строка содержит /*, считаем ссылки комментарийными
            in_block_comment = True
            for m in REF_RE.finditer(line):
                full = m.group(0)
                if f"objects/{obj_prefix}/" in full:
                    commented[m.group(1)].append((line_no, line.rstrip()))
            continue

        # Однострочный комментарий
        is_commented = is_line_commented(line)

        for m in REF_RE.finditer(line):
            full = m.group(0)
            if f"objects/{obj_prefix}/" not in full:
                continue
            rel = m.group(1)

            if is_commented:
                commented[rel].append((line_no, line.rstrip()))
            else:
                # Ещё проверяем: может ссылка идёт ПОСЛЕ // в той же строке
                pos = line.find("//")
                if pos >= 0 and m.start() > pos:
                    commented[rel].append((line_no, line.rstrip()))
                else:
                    active.add(rel)

    return active, commented


def find_comment_orphans(cabinet: str) -> tuple[
    set[str],
    dict[str, list[tuple[Path, int, str]]],
    set[str]
]:
    """Находит comment-orphan файлы для шкафа.

    Returns:
        comment_orphans  — set относительных путей файлов-сирот
        orphan_locations — {rel_path: [(file, line_no, line_text), ...]}
        pure_orphans     — файлы вообще без ссылок (обычные сироты)
    """
    obj_prefix = f"objects_{cabinet}"
    obj_dir = OBJECTS_DIR / obj_prefix

    if not obj_dir.is_dir():
        return set(), {}, set()

    # Все XML в objects_<ШКАФ>/
    all_files: set[str] = set()
    for f in obj_dir.rglob("*.xml"):
        rel = str(f.relative_to(obj_dir)).replace("\\", "/")
        all_files.add(rel)

    # Собираем ссылки из мнемосхем + объектов
    active_global: set[str] = set()
    commented_global: dict[str, list[tuple[Path, int, str]]] = defaultdict(list)

    scan_dirs = []
    mnemo = MNEMO_DIR / cabinet
    if mnemo.is_dir():
        scan_dirs.append(mnemo)
    if obj_dir.is_dir():
        scan_dirs.append(obj_dir)

    for scan_dir in scan_dirs:
        for xml_file in scan_dir.rglob("*.xml"):
            active, commented = classify_refs_in_file(xml_file, obj_prefix)
            active_global.update(active)
            for rel, locs in commented.items():
                for line_no, line_text in locs:
                    commented_global[rel].append((xml_file, line_no, line_text))

    # Итеративно расширяем active (файл A ссылается на B → B активен)
    prev = -1
    while len(active_global) != prev:
        prev = len(active_global)
        for rel in list(active_global):
            fpath = obj_dir / rel
            if fpath.exists():
                a, _ = classify_refs_in_file(fpath, obj_prefix)
                active_global.update(a)

    # Классификация
    comment_only = set()
    pure_orphans = set()

    for rel in all_files:
        if rel in active_global:
            continue
        if rel in commented_global:
            comment_only.add(rel)
        else:
            pure_orphans.add(rel)

    return comment_only, commented_global, pure_orphans


def remove_commented_lines(filepath: Path, line_numbers: set[int]) -> int:
    """Удаляет строки по номерам из файла. Возвращает кол-во удалённых."""
    text = read_text_safe(filepath)
    if not text:
        return 0

    lines = text.splitlines(keepends=True)
    new_lines = []
    removed = 0

    for i, line in enumerate(lines, 1):
        if i in line_numbers:
            removed += 1
            # Проверяем — следующие строки тоже могут быть частью блока
            # (многострочный закомментированный вызов)
        else:
            new_lines.append(line)

    if removed:
        filepath.write_text("".join(new_lines), encoding="utf-8", newline="\n")

    return removed


def clean_commented_block(filepath: Path, start_line: int) -> list[int]:
    """Находит полный закомментированный блок начиная со строки start_line.

    Например:
      //  if (objName.contains("P1V1")){
      //    ChildPanelOnRelativ("objects/...xml",
      //      "Теплоконтроль",
      //      makeDynString(...),
      //      309, 480);
      //  }

    Возвращает список номеров строк блока.
    """
    text = read_text_safe(filepath)
    if not text:
        return []

    lines = text.splitlines()
    block_lines = []

    # Идём назад от start_line, ищем начало блока (первый //)
    idx = start_line - 1  # 0-based
    while idx > 0 and is_line_commented(lines[idx - 1]):
        # Проверяем — это связанный блок (не просто рядом стоящие комментарии)
        # Если предыдущая строка — пустой комментарий или совсем другой код, стоп
        prev = lines[idx - 1].strip()
        if prev == "//" or prev == "":
            break
        idx -= 1

    # Идём вперёд от начала блока
    for i in range(idx, len(lines)):
        if is_line_commented(lines[i]):
            block_lines.append(i + 1)  # 1-based
        else:
            break

    return block_lines


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Удаление закомментированных ссылок на фейсплейты и файлов-сирот"
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="Реально удалить файлы и комментарии (по умолчанию — dry-run)"
    )
    parser.add_argument(
        "cabinets", nargs="*",
        help="Шкафы для обработки (по умолчанию — все)"
    )
    args = parser.parse_args()
    apply = args.apply
    mode_label = "APPLY" if apply else "DRY-RUN"

    # Определяем шкафы
    if args.cabinets:
        cabinets = args.cabinets
    else:
        active = load_active_cabinets()
        if active:
            cabinets = sorted(active)
        else:
            cabinets = sorted(
                d.name.removeprefix("objects_")
                for d in OBJECTS_DIR.iterdir()
                if d.is_dir() and d.name.startswith("objects_")
            )

    print(f"Режим: {mode_label}")
    print(f"Шкафов: {len(cabinets)}")
    print()

    report_lines: list[str] = []
    report_lines.append(f"Clean Commented Refs Report ({mode_label})")
    report_lines.append("=" * 60)

    total_comment_orphans = 0
    total_pure_orphans = 0
    total_lines_removed = 0
    total_files_deleted = 0

    for cabinet in cabinets:
        comment_orphans, orphan_locs, pure_orphans = find_comment_orphans(cabinet)

        if not comment_orphans and not pure_orphans:
            continue

        print(f"{'='*60}")
        print(f"Шкаф: {cabinet}")
        print(f"{'='*60}")

        report_lines.append("")
        report_lines.append(f"[{cabinet}]")

        obj_dir = OBJECTS_DIR / f"objects_{cabinet}"

        # --- Comment orphans ---
        if comment_orphans:
            print(f"  Comment orphans: {len(comment_orphans)}")
            report_lines.append(f"  Comment orphans: {len(comment_orphans)}")

            for rel in sorted(comment_orphans):
                print(f"    ✗ {rel}")
                report_lines.append(f"    ✗ {rel}")

                # Показываем где ссылка
                for src_file, line_no, line_text in orphan_locs.get(rel, []):
                    src_rel = src_file.relative_to(MODULES_DIR)
                    short = line_text.strip()[:100]
                    print(f"      L{line_no} in {src_rel}: {short}")
                    report_lines.append(f"      L{line_no} in {src_rel}")

                    # Удаляем блок комментариев
                    if apply:
                        block = clean_commented_block(src_file, line_no)
                        if block:
                            removed = remove_commented_lines(src_file, set(block))
                            total_lines_removed += removed
                            print(f"        → удалено {removed} строк комментариев")

                # Удаляем файл
                fpath = obj_dir / rel
                if fpath.exists() and apply:
                    fpath.unlink()
                    total_files_deleted += 1
                    print(f"      → файл удалён")

            total_comment_orphans += len(comment_orphans)

        # --- Pure orphans (вообще без ссылок) ---
        if pure_orphans:
            print(f"  Pure orphans (нет ссылок вообще): {len(pure_orphans)}")
            report_lines.append(f"  Pure orphans: {len(pure_orphans)}")

            for rel in sorted(pure_orphans):
                print(f"    ○ {rel}")
                report_lines.append(f"    ○ {rel}")

                fpath = obj_dir / rel
                if fpath.exists() and apply:
                    fpath.unlink()
                    total_files_deleted += 1
                    print(f"      → файл удалён")

            total_pure_orphans += len(pure_orphans)

    # Итого
    print()
    print(f"{'='*60}")
    print(f"ИТОГО:")
    print(f"  Comment orphans: {total_comment_orphans}")
    print(f"  Pure orphans:    {total_pure_orphans}")
    if apply:
        print(f"  Файлов удалено:  {total_files_deleted}")
        print(f"  Строк удалено:   {total_lines_removed}")
    print(f"{'='*60}")

    # Сохраняем отчёт
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_file = REPORT_DIR / "commented_refs_report.txt"
    report_lines.append("")
    report_lines.append(f"Comment orphans: {total_comment_orphans}")
    report_lines.append(f"Pure orphans:    {total_pure_orphans}")
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines) + "\n")
    print(f"\nОтчёт: {report_file}")


if __name__ == "__main__":
    main()
