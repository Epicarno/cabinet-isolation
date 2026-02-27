#!/usr/bin/env python3
"""
clean_dpl.py — Очистка DPL-файлов: удаление лишних точек и CNS-сирот.

Удаляет из DPL-файлов:
  - DP-инстансы по списку (из файла или аргументов)
  - Все связанные записи во ВСЕХ секциях DPL
  - CNS-сиротские ссылки (на несуществующие DP)
  - Неиспользуемые DpType (опционально)

Затрагиваемые секции:
  # Datapoint/DpId, # Aliases/Comments, # DpValue,
  # DistributionInfo, # DpFunction, # DpConvRawToIngMain,
  # DpConvIngToRawMain, # PeriphAddrMain, # DbArchiveInfo,
  # AlertValue, # CNS

Использование:
  python clean_dpl.py SHD_03_1 --remove SHD_03_1>ITP2>AI>P3 SHD_03_1>ITP2>AI>P4
  python clean_dpl.py SHD_03_1 --remove-file remove_list.txt
  python clean_dpl.py SHD_03_1 --clean-cns-orphans
  python clean_dpl.py SHD_03_1 --remove-unused-types
  python clean_dpl.py SHD_03_1 --dry-run --remove-file remove_list.txt

  Комбинации:
  python clean_dpl.py SHD_03_1 --remove-file list.txt --clean-cns-orphans --dry-run
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

# Windows cp1251 ломает Unicode-символы → форсируем UTF-8
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
from collections import defaultdict
from datetime import datetime

# ---------------------------------------------------------------------------
SCRIPT_DIR  = Path(__file__).resolve().parent
SCRIPTS_DIR = SCRIPT_DIR.parent          # rename/
MODULES_DIR = SCRIPTS_DIR.parent.parent   # Modules/
DPL_DIR     = MODULES_DIR / "DPLs"


def extract_dp_name(element_ref: str) -> str:
    """Извлекает базовое имя DP из 'DpName.element.sub' → 'DpName'.

    Для имён с >: SHD_03_1>UURV>AI>FE1.Value → SHD_03_1>UURV>AI>FE1
    Для имён с _: SHUOD_03_1_StSign_1.State.P → SHUOD_03_1_StSign_1
    Для 'DpName.' (корень алиаса): → DpName
    """
    dot_pos = element_ref.find(".")
    if dot_pos >= 0:
        return element_ref[:dot_pos]
    return element_ref


def parse_sections(text: str) -> list[tuple[str, int, int]]:
    """Разбивает DPL-текст на секции: [(section_name, start_line, end_line), ...].

    start_line/end_line — 0-based индексы строк.
    """
    lines = text.splitlines()
    sections: list[tuple[str, int, int]] = []
    current_name = "__header__"
    current_start = 0

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("# ") and len(stripped) > 2:
            # Новая секция
            if current_name:
                sections.append((current_name, current_start, i))
            current_name = stripped
            current_start = i

    # Последняя секция
    if current_name:
        sections.append((current_name, current_start, len(lines)))

    return sections


def collect_all_dps(dpl_dir: Path) -> set[str]:
    """Собирает ВСЕ DP-имена из всех DPL-файлов шкафа."""
    all_dps: set[str] = set()
    for dpl_file in sorted(dpl_dir.glob("*.dpl")):
        try:
            text = dpl_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        in_section = False
        for line in text.splitlines():
            stripped = line.strip()
            if stripped == "# Datapoint/DpId":
                in_section = True
                continue
            if stripped.startswith("# ") and in_section and stripped != "# Datapoint/DpId":
                in_section = False
                continue
            if not in_section or not stripped or stripped.startswith("DpName\t"):
                continue
            parts = stripped.split("\t")
            if len(parts) >= 3:
                all_dps.add(parts[0].strip())
    return all_dps


def clean_dpl_file(dpl_path: Path,
                   remove_dps: set[str],
                   all_existing_dps: set[str],
                   clean_cns: bool,
                   remove_unused_types: bool,
                   dry_run: bool) -> dict[str, int]:
    """Очищает один DPL-файл. Возвращает статистику удалений по секциям."""
    text = dpl_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    sections = parse_sections(text)

    stats: dict[str, int] = defaultdict(int)
    remove_lines: set[int] = set()

    # Используем all_existing_dps (собраны из ВСЕХ DPL шкафа),
    # минус те, что удаляем
    existing_dps = all_existing_dps - remove_dps

    for sec_name, sec_start, sec_end in sections:

        # ── # Datapoint/DpId ──────────────────────────────────────
        if sec_name == "# Datapoint/DpId":
            for i in range(sec_start + 1, sec_end):
                line = lines[i].strip()
                if not line or line.startswith("DpName\t"):
                    continue
                parts = line.split("\t")
                if len(parts) >= 3:
                    dp_name = parts[0].strip()
                    if dp_name in remove_dps:
                        remove_lines.add(i)
                        stats["Datapoint/DpId"] += 1

        # ── # Aliases/Comments ────────────────────────────────────
        elif sec_name == "# Aliases/Comments":
            for i in range(sec_start + 1, sec_end):
                line = lines[i].strip()
                if not line or line.startswith("AliasId\t"):
                    continue
                parts = line.split("\t")
                if parts:
                    dp = extract_dp_name(parts[0].strip())
                    if dp in remove_dps:
                        remove_lines.add(i)
                        stats["Aliases/Comments"] += 1

        # ── Секции с DP в поле 2 ──────────────────────────────────
        elif sec_name in ("# DpValue", "# DistributionInfo",
                          "# DpConvRawToIngMain", "# DpConvIngToRawMain",
                          "# PeriphAddrMain", "# DbArchiveInfo",
                          "# AlertValue"):
            for i in range(sec_start + 1, sec_end):
                line = lines[i].strip()
                if not line or "\t" not in line:
                    continue
                # Пропускаем заголовок секции
                if any(line.startswith(h) for h in ("Manager/User\t",)):
                    continue
                parts = line.split("\t")
                if len(parts) >= 3:
                    element_ref = parts[1].strip()
                    dp = extract_dp_name(element_ref)
                    if dp in remove_dps:
                        remove_lines.add(i)
                        stats[sec_name.replace("# ", "")] += 1

        # ── # DpFunction (поле 2 + ссылки в поле 5) ──────────────
        elif sec_name == "# DpFunction":
            for i in range(sec_start + 1, sec_end):
                line = lines[i].strip()
                if not line or line.startswith("Manager/User\t"):
                    continue
                parts = line.split("\t")
                if len(parts) >= 3:
                    element_ref = parts[1].strip()
                    dp = extract_dp_name(element_ref)
                    if dp in remove_dps:
                        remove_lines.add(i)
                        stats["DpFunction"] += 1

        # ── # CNS ─────────────────────────────────────────────────
        elif sec_name == "# CNS" and clean_cns:
            for i in range(sec_start + 1, sec_end):
                line = lines[i]
                # CNS-ссылки: 720896 DpName.Element в поле data (5-е)
                m = re.search(r'720896\s+(\S+)', line)
                if m:
                    dp = extract_dp_name(m.group(1))
                    # Удаляем если DP в списке удаления ИЛИ DP не существует
                    if dp in remove_dps:
                        remove_lines.add(i)
                        stats["CNS (удалённые DP)"] += 1
                    elif dp not in existing_dps:
                        remove_lines.add(i)
                        stats["CNS (сироты)"] += 1

    # ── Удаление неиспользуемых DpType ────────────────────────────
    if remove_unused_types:
        # Собираем типы, которые остаются после удаления
        remaining_types: set[str] = set()
        for sec_name, sec_start, sec_end in sections:
            if sec_name == "# Datapoint/DpId":
                for i in range(sec_start + 1, sec_end):
                    if i in remove_lines:
                        continue
                    line = lines[i].strip()
                    if not line or line.startswith("DpName\t"):
                        continue
                    parts = line.split("\t")
                    if len(parts) >= 3:
                        remaining_types.add(parts[1].strip())

        # Удаляем определения типов, которые больше не используются
        for sec_name, sec_start, sec_end in sections:
            if sec_name == "# DpType":
                current_type = None
                type_lines: dict[str, list[int]] = defaultdict(list)

                for i in range(sec_start + 1, sec_end):
                    line = lines[i]
                    stripped = line.strip()
                    if not stripped or stripped == "TypeName":
                        continue

                    # Корневой тип: TAIRA_PUMP.TAIRA_PUMP\t1#1
                    if not line.startswith("\t") and "." in stripped:
                        parts = stripped.split("\t")
                        if len(parts) >= 2 and "." in parts[0]:
                            current_type = parts[0].split(".")[0]
                            type_lines[current_type].append(i)
                            continue

                    # Вложенный элемент
                    if current_type and line.startswith("\t"):
                        type_lines[current_type].append(i)

                for type_name, line_indices in type_lines.items():
                    if type_name not in remaining_types:
                        for i in line_indices:
                            remove_lines.add(i)
                        stats["DpType (неисп.)"] += len(line_indices)

    if not remove_lines:
        return dict(stats)

    # Формируем результат
    new_lines = [line for i, line in enumerate(lines) if i not in remove_lines]

    if dry_run:
        return dict(stats)

    # Бэкап
    backup_dir = dpl_path.parent / "backup"
    backup_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"{dpl_path.stem}_{timestamp}{dpl_path.suffix}"
    shutil.copy2(dpl_path, backup_path)

    # Записываем
    dpl_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    return dict(stats)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Очистка DPL-файлов от лишних точек и CNS-сирот"
    )
    parser.add_argument("cabinet", help="Имя шкафа (напр. SHD_03_1)")
    parser.add_argument(
        "--remove", nargs="*", default=[],
        help="DP-имена для удаления (через пробел)"
    )
    parser.add_argument(
        "--remove-file", type=Path, default=None,
        help="Файл со списком DP для удаления (по одному на строку)"
    )
    parser.add_argument(
        "--clean-cns-orphans", action="store_true",
        help="Удалить CNS-ссылки на несуществующие DP"
    )
    parser.add_argument(
        "--remove-unused-types", action="store_true",
        help="Удалить DpType, которые больше не используются"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Только показать что будет удалено, не менять файлы"
    )
    args = parser.parse_args()

    # Собираем список DP для удаления
    remove_dps: set[str] = set(args.remove)

    if args.remove_file:
        if not args.remove_file.exists():
            print(f"ОШИБКА: файл не найден: {args.remove_file}", file=sys.stderr)
            sys.exit(1)
        for line in args.remove_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                remove_dps.add(line)

    if not remove_dps and not args.clean_cns_orphans and not args.remove_unused_types:
        print("Нечего делать. Укажите --remove, --remove-file,")
        print("--clean-cns-orphans или --remove-unused-types")
        sys.exit(1)

    dpl_cab_dir = DPL_DIR / args.cabinet
    if not dpl_cab_dir.is_dir():
        print(f"ОШИБКА: папка не найдена: {dpl_cab_dir}", file=sys.stderr)
        sys.exit(1)

    mode = "DRY-RUN" if args.dry_run else "ОЧИСТКА"
    print(f"\n{'═'*60}")
    print(f" {mode}: {args.cabinet}")
    print(f"{'═'*60}")

    if remove_dps:
        print(f"  DP для удаления: {len(remove_dps)}")
    if args.clean_cns_orphans:
        print(f"  Очистка CNS-сирот: да")
    if args.remove_unused_types:
        print(f"  Удаление неисп. типов: да")

    total_stats: dict[str, int] = defaultdict(int)
    total_removed = 0

    # Собираем ВСЕ DP из всех DPL шкафа (для CNS-проверки)
    all_existing_dps = collect_all_dps(dpl_cab_dir)
    print(f"  Всего DP в DPL: {len(all_existing_dps)}")

    for dpl_file in sorted(dpl_cab_dir.glob("*.dpl")):
        print(f"\n{'─'*60}")
        print(f"  Файл: {dpl_file.name}")
        print(f"{'─'*60}")

        is_cns = dpl_file.name == "cns.dpl"
        stats = clean_dpl_file(
            dpl_file,
            remove_dps=remove_dps,
            all_existing_dps=all_existing_dps,
            clean_cns=args.clean_cns_orphans or is_cns,
            remove_unused_types=args.remove_unused_types,
            dry_run=args.dry_run,
        )

        if stats:
            for sec, count in sorted(stats.items()):
                print(f"    {sec:<30s} {count:>5d} строк")
                total_stats[sec] += count
                total_removed += count
        else:
            print(f"    (ничего не удалено)")

    print(f"\n{'═'*60}")
    print(f" ИТОГО: {total_removed} строк {'будет удалено' if args.dry_run else 'удалено'}")
    print(f"{'═'*60}")
    for sec, count in sorted(total_stats.items()):
        print(f"  {sec:<30s} {count:>5d}")

    if not args.dry_run and total_removed > 0:
        print(f"\n  Бэкапы в: {dpl_cab_dir / 'backup'}")
    elif args.dry_run and total_removed > 0:
        print(f"\n  Для применения — уберите --dry-run")


if __name__ == "__main__":
    main()
