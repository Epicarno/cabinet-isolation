#!/usr/bin/env python3
"""
validate_dpl_points.py — Комплексная валидация точек DPL.

Проверки:
  1) DPL ↔ мнемосхемы: лишние точки в DPL, пропущенные в DPL
  2) CSV struct ↔ DPL-тип инстанса: поточечная статистика совпадений
  3) CNS ↔ DPL: ссылки на несуществующие DP, DP без CNS-записи
  4) _Static анализ: на каких мнемосхемах, есть ли в DPL

Выход (reports/datapoints/):
  _dpl_vs_mnemo.txt       — DPL ↔ мнемосхемы
  _dpl_vs_csv_types.txt   — CSV struct vs DPL тип (статистика)
  _cns_orphans.txt        — CNS ↔ DPL расхождения
  _static_analysis.txt    — анализ _Static точек

Использование:
  python validate_dpl_points.py                # шкафы из cabinets.txt
  python validate_dpl_points.py SHD_03_1       # один шкаф
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Windows cp1251 ломает Unicode-символы → форсируем UTF-8
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
from collections import defaultdict

# ---------------------------------------------------------------------------
SCRIPT_DIR  = Path(__file__).resolve().parent
SCRIPTS_DIR = SCRIPT_DIR.parent          # rename/
MODULES_DIR = SCRIPTS_DIR.parent.parent   # Modules/
MNEMO_DIR   = MODULES_DIR / "ventcontent" / "panels" / "vision" / "LCSMnemo"
DPL_DIR     = MODULES_DIR / "DPLs"
REPORT_DIR  = MODULES_DIR / "reports" / "datapoints"


# ═══════════════════════════════════════════════════════════════════════════
# Парсеры
# ═══════════════════════════════════════════════════════════════════════════

def parse_dpl_instances(dpl_path: Path) -> dict[str, str]:
    """Извлекает DP-инстансы: dpName → DpType.

    Формат секции # Datapoint/DpId:
      DpName\tTypeName\tID
      SHD_03_1>UURV>AI>FE1\tTAIRA_AI\t604587
    """
    instances: dict[str, str] = {}
    in_section = False

    try:
        text = dpl_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return instances

    for line in text.splitlines():
        stripped = line.strip()

        if stripped == "# Datapoint/DpId":
            in_section = True
            continue
        if stripped.startswith("# ") and in_section and stripped != "# Datapoint/DpId":
            in_section = False
            continue

        if not in_section or not stripped:
            continue

        # Пропускаем заголовок
        if stripped == "DpName\tTypeName\tID":
            continue

        parts = stripped.split("\t")
        if len(parts) >= 3:
            dp_name = parts[0].strip()
            dp_type = parts[1].strip()
            # Пропускаем служебные (_ds_*, testAlert и т.п.)
            if dp_name and not dp_name.startswith("_") and dp_name != "testAlert>ITP":
                instances[dp_name] = dp_type

    return instances


def parse_cns_references(cns_path: Path) -> dict[str, set[str]]:
    """Извлекает DP-ссылки из CNS: dpName → {element1, element2, ...}.

    Формат: 720896 SHD_03_1>A1-A16>ZD>K1_12.state.emergency
    DP-имя — часть до первой точки после последнего >.
    """
    dp_refs: dict[str, set[str]] = defaultdict(set)
    pattern = re.compile(r'720896\s+(\S+)')

    try:
        text = cns_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return dp_refs

    for match in pattern.finditer(text):
        full_ref = match.group(1)

        # Разделяем: dpName.element.subelement
        # DP с > в имени: SHD_03_1>A1-A16>ZD>K1_12.state.emergency
        # DP с _ в имени: SHUOD_03_1_StSign_1.State (нет >)
        #
        # Находим первую точку — это граница dpName и element
        dot_pos = full_ref.find(".")
        if dot_pos >= 0:
            dp_name = full_ref[:dot_pos]
            element = full_ref[dot_pos + 1:]
        else:
            dp_name = full_ref
            element = ""

        if dp_name:
            dp_refs[dp_name].add(element)

    return dp_refs


def load_mnemo_points(mnemo_dir: Path, cabinet: str) -> dict[str, set[str]]:
    """Загружает точки мнемосхем из XML + CSV: dp → {мнемосхема1, мнемосхема2}.

    Прямой парсинг (не из отчётов), чтобы знать, на какой мнемосхеме
    сидит каждая точка.
    """
    dp_pattern = re.compile(r'Name="([^"]*>[^"]*>[^"]*)"')
    dp_mnemos: dict[str, set[str]] = defaultdict(set)

    cab_dir = mnemo_dir / cabinet
    if not cab_dir.is_dir():
        return dp_mnemos

    # XML — точки с > в Name=""
    for xml_file in sorted(cab_dir.rglob("*.xml")):
        try:
            text = xml_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        mnemo = xml_file.stem
        for m in dp_pattern.finditer(text):
            dp_mnemos[m.group(1)].add(mnemo)

    # CSV — refName + dpName
    for csv_file in sorted(cab_dir.glob("*.csv")):
        try:
            text = csv_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        mnemo = csv_file.stem
        for line in text.strip().split("\n")[1:]:
            parts = line.split(",")
            if len(parts) < 2:
                continue
            ref_name = parts[0].strip()
            dp_name = parts[1].strip()

            # Принадлежность шкафу
            if not ref_name.startswith(cabinet) and not dp_name.startswith(cabinet):
                continue

            if ref_name:
                dp_mnemos[ref_name].add(mnemo)
            if dp_name:
                for dp in dp_name.split("|"):
                    dp = dp.strip()
                    if dp and dp != ref_name:
                        dp_mnemos[dp].add(mnemo)

    return dp_mnemos


def load_csv_struct_map(mnemo_dir: Path,
                        cabinet: str) -> dict[str, tuple[str, str]]:
    """dpName → (struct, csv_file). Для поточечной сверки с DPL-типом."""
    mapping: dict[str, tuple[str, str]] = {}

    cab_dir = mnemo_dir / cabinet
    if not cab_dir.is_dir():
        return mapping

    for csv_file in sorted(cab_dir.glob("*.csv")):
        try:
            text = csv_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for line in text.strip().split("\n")[1:]:
            parts = line.split(",")
            if len(parts) < 5:
                continue
            ref_name = parts[0].strip()
            dp_name = parts[1].strip()
            struct = parts[4].strip()

            if not struct:
                continue
            if not ref_name.startswith(cabinet) and not dp_name.startswith(cabinet):
                continue

            key = dp_name if dp_name else ref_name
            if key:
                mapping[key] = (struct, csv_file.name)
            if ref_name and ref_name != key:
                mapping[ref_name] = (struct, csv_file.name)

    return mapping


def load_csv_static_details(mnemo_dir: Path,
                            cabinet: str
                            ) -> dict[str, list[tuple[str, str, str]]]:
    """struct (с _Static) → [(dpName, описание, csv_file), ...]."""
    statics: dict[str, list[tuple[str, str, str]]] = defaultdict(list)

    cab_dir = mnemo_dir / cabinet
    if not cab_dir.is_dir():
        return statics

    for csv_file in sorted(cab_dir.glob("*.csv")):
        try:
            text = csv_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for line in text.strip().split("\n")[1:]:
            parts = line.split(",")
            if len(parts) < 5:
                continue
            ref_name = parts[0].strip()
            dp_name = parts[1].strip()
            struct = parts[4].strip()
            desc = parts[5].strip() if len(parts) > 5 else ""

            if not struct.endswith("_Static"):
                continue
            if not ref_name.startswith(cabinet) and not dp_name.startswith(cabinet):
                continue

            key = dp_name if dp_name else ref_name
            statics[struct].append((key, desc, csv_file.name))

    return statics


# ═══════════════════════════════════════════════════════════════════════════
# Основная логика
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Комплексная валидация точек DPL"
    )
    parser.add_argument(
        "cabinets", nargs="*",
        help="Шкафы для обработки (по умолчанию — из cabinets.txt)"
    )
    args = parser.parse_args()

    if args.cabinets:
        cabinets = args.cabinets
    else:
        cabinets_file = SCRIPTS_DIR / "cabinets.txt"
        if cabinets_file.exists():
            cabinets = [
                line.strip()
                for line in cabinets_file.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.strip().startswith("#")
            ]
        else:
            if DPL_DIR.exists():
                cabinets = sorted(d.name for d in DPL_DIR.iterdir() if d.is_dir())
            else:
                print(f"ОШИБКА: не найдена папка {DPL_DIR}", file=sys.stderr)
                sys.exit(1)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    for cabinet in cabinets:
        print(f"\n{'═'*70}")
        print(f" ШКАФ: {cabinet}")
        print(f"{'═'*70}")

        # ──────────────────────────────────────────────────────────────
        # Загрузка данных
        # ──────────────────────────────────────────────────────────────
        dpl_cab_dir = DPL_DIR / cabinet

        # DPL инстансы
        dpl_instances: dict[str, str] = {}
        if dpl_cab_dir.is_dir():
            for dpl_file in sorted(dpl_cab_dir.glob("*.dpl")):
                if dpl_file.name == "cns.dpl":
                    continue
                insts = parse_dpl_instances(dpl_file)
                print(f"  DPL: {dpl_file.name} → {len(insts)} инстансов")
                dpl_instances.update(insts)

        # Мнемосхемы
        mnemo_points = load_mnemo_points(MNEMO_DIR, cabinet)
        print(f"  Мнемосхемы: {len(mnemo_points)} точек")

        # CSV struct → dp
        csv_map = load_csv_struct_map(MNEMO_DIR, cabinet)

        # CNS
        cns_refs: dict[str, set[str]] = {}
        cns_path = dpl_cab_dir / "cns.dpl" if dpl_cab_dir.is_dir() else None
        if cns_path and cns_path.exists():
            cns_refs = parse_cns_references(cns_path)
            print(f"  CNS: {len(cns_refs)} уникальных DP-ссылок")

        # ══════════════════════════════════════════════════════════════
        # 1. DPL ↔ мнемосхемы
        # ══════════════════════════════════════════════════════════════
        print(f"\n{'─'*60}")
        print(f" 1. DPL ↔ МНЕМОСХЕМЫ")
        print(f"{'─'*60}")

        dpl_set = set(dpl_instances.keys())
        mnemo_set = set(mnemo_points.keys())

        # Точки только в DPL (лишние?)
        dpl_only = sorted(dpl_set - mnemo_set)
        # Точки только на мнемосхемах (пропущены в DPL?)
        mnemo_only = sorted(mnemo_set - dpl_set)
        # Общие
        common = dpl_set & mnemo_set

        report_mnemo = []
        report_mnemo.append(f"{'═'*60}")
        report_mnemo.append(f"ШКАФ: {cabinet} — DPL ↔ мнемосхемы")
        report_mnemo.append(f"{'═'*60}")
        report_mnemo.append(f"  DPL инстансов:  {len(dpl_set)}")
        report_mnemo.append(f"  Мнемо точек:    {len(mnemo_set)}")
        report_mnemo.append(f"  Совпадают:      {len(common)}")
        report_mnemo.append(f"  Только в DPL:   {len(dpl_only)}")
        report_mnemo.append(f"  Только на мнемо:{len(mnemo_only)}")

        print(f"  Совпадают:       {len(common)}")
        print(f"  Только в DPL:    {len(dpl_only)} (лишние в DPL?)")
        print(f"  Только на мнемо: {len(mnemo_only)} (пропущены в DPL?)")

        if dpl_only:
            report_mnemo.append(f"\n{'─'*60}")
            report_mnemo.append(f"ТОЛЬКО В DPL — {len(dpl_only)} точек (нет на мнемосхемах)")
            report_mnemo.append(f"{'─'*60}")

            # Группируем по типу
            by_type: dict[str, list[str]] = defaultdict(list)
            for dp in dpl_only:
                by_type[dpl_instances[dp]].append(dp)

            for typ in sorted(by_type.keys()):
                dps = by_type[typ]
                report_mnemo.append(f"\n  [{typ}] — {len(dps)} точек:")
                for dp in sorted(dps):
                    report_mnemo.append(f"    {dp}")

        if mnemo_only:
            report_mnemo.append(f"\n{'─'*60}")
            report_mnemo.append(f"ТОЛЬКО НА МНЕМО — {len(mnemo_only)} точек (нет в DPL)")
            report_mnemo.append(f"{'─'*60}")

            for dp in mnemo_only:
                mnemos = ", ".join(sorted(mnemo_points[dp]))
                report_mnemo.append(f"  {dp:<55s} [{mnemos}]")

        f1 = REPORT_DIR / f"{cabinet}_dpl_vs_mnemo.txt"
        f1.write_text("\n".join(report_mnemo), encoding="utf-8")
        print(f"  → {f1.name}")

        # ══════════════════════════════════════════════════════════════
        # 2. CSV struct ↔ DPL тип инстанса (статистика)
        # ══════════════════════════════════════════════════════════════
        print(f"\n{'─'*60}")
        print(f" 2. CSV struct ↔ DPL тип инстанса")
        print(f"{'─'*60}")

        match_count = 0
        mismatch_count = 0
        no_csv = 0
        no_dpl = 0
        mismatches: list[tuple[str, str, str]] = []  # (dp, csv_struct, dpl_type)

        # Проверяем для каждой точки, которая есть и в DPL и в CSV
        all_dps = dpl_set | set(csv_map.keys())
        for dp in sorted(all_dps):
            in_dpl = dp in dpl_instances
            in_csv = dp in csv_map

            if in_dpl and in_csv:
                dpl_type = dpl_instances[dp]
                csv_struct = csv_map[dp][0]
                if csv_struct == dpl_type:
                    match_count += 1
                else:
                    mismatch_count += 1
                    mismatches.append((dp, csv_struct, dpl_type))
            elif in_dpl and not in_csv:
                no_csv += 1
            elif in_csv and not in_dpl:
                no_dpl += 1

        report_types = []
        report_types.append(f"{'═'*60}")
        report_types.append(f"ШКАФ: {cabinet} — CSV struct ↔ DPL тип инстанса")
        report_types.append(f"{'═'*60}")
        report_types.append(f"  Совпадают:         {match_count}")
        report_types.append(f"  НЕ совпадают:      {mismatch_count}")
        report_types.append(f"  В DPL, нет в CSV:  {no_csv}")
        report_types.append(f"  В CSV, нет в DPL:  {no_dpl}")

        print(f"  Совпадают:          {match_count}")
        print(f"  НЕ совпадают:       {mismatch_count}")
        print(f"  В DPL, нет в CSV:   {no_csv}")
        print(f"  В CSV, нет в DPL:   {no_dpl}")

        if mismatches:
            report_types.append(f"\n{'─'*60}")
            report_types.append(f"НЕСОВПАДЕНИЯ — {len(mismatches)}")
            report_types.append(f"{'─'*60}")
            report_types.append(
                f"  {'DP':<50s} {'CSV struct':<25s} {'DPL тип':<25s}"
            )
            report_types.append(f"  {'─'*48} {'─'*23} {'─'*23}")
            for dp, csv_s, dpl_t in mismatches:
                report_types.append(f"  {dp:<50s} {csv_s:<25s} {dpl_t:<25s}")
                print(f"    {dp}: CSV={csv_s}, DPL={dpl_t}")

        f2 = REPORT_DIR / f"{cabinet}_dpl_vs_csv_types.txt"
        f2.write_text("\n".join(report_types), encoding="utf-8")
        print(f"  → {f2.name}")

        # ══════════════════════════════════════════════════════════════
        # 3. CNS ↔ DPL
        # ══════════════════════════════════════════════════════════════
        if cns_refs:
            print(f"\n{'─'*60}")
            print(f" 3. CNS ↔ DPL")
            print(f"{'─'*60}")

            cns_dp_set = set(cns_refs.keys())

            # CNS ссылки на DP, которых нет в DPL
            cns_orphans = sorted(cns_dp_set - dpl_set)
            # DPL инстансы без CNS-записи
            no_cns = sorted(dpl_set - cns_dp_set)

            print(f"  CNS DP-ссылок:     {len(cns_dp_set)}")
            print(f"  CNS → нет в DPL:  {len(cns_orphans)} (сиротские ссылки)")
            print(f"  DPL → нет в CNS:  {len(no_cns)} (без навигации)")

            report_cns = []
            report_cns.append(f"{'═'*60}")
            report_cns.append(f"ШКАФ: {cabinet} — CNS ↔ DPL")
            report_cns.append(f"{'═'*60}")
            report_cns.append(f"  CNS DP-ссылок:     {len(cns_dp_set)}")
            report_cns.append(f"  DPL инстансов:     {len(dpl_set)}")
            report_cns.append(f"  Общих:             {len(cns_dp_set & dpl_set)}")
            report_cns.append(f"  CNS → нет в DPL:  {len(cns_orphans)}")
            report_cns.append(f"  DPL → нет в CNS:  {len(no_cns)}")

            if cns_orphans:
                report_cns.append(f"\n{'─'*60}")
                report_cns.append(f"CNS-СИРОТЫ — {len(cns_orphans)} (ссылки на несуществующие DP)")
                report_cns.append(f"{'─'*60}")
                for dp in cns_orphans:
                    elements = ", ".join(sorted(cns_refs[dp]))
                    report_cns.append(f"  {dp:<55s} [{elements}]")

            if no_cns:
                report_cns.append(f"\n{'─'*60}")
                report_cns.append(f"BEЗ CNS — {len(no_cns)} DPL-инстансов без навигации")
                report_cns.append(f"{'─'*60}")

                by_type_nc: dict[str, list[str]] = defaultdict(list)
                for dp in no_cns:
                    by_type_nc[dpl_instances[dp]].append(dp)
                for typ in sorted(by_type_nc.keys()):
                    dps = by_type_nc[typ]
                    report_cns.append(f"\n  [{typ}] — {len(dps)}:")
                    for dp in sorted(dps):
                        report_cns.append(f"    {dp}")

            f3 = REPORT_DIR / f"{cabinet}_cns_orphans.txt"
            f3.write_text("\n".join(report_cns), encoding="utf-8")
            print(f"  → {f3.name}")

        # ══════════════════════════════════════════════════════════════
        # 4. _Static анализ
        # ══════════════════════════════════════════════════════════════
        static_details = load_csv_static_details(MNEMO_DIR, cabinet)

        if static_details:
            print(f"\n{'─'*60}")
            print(f" 4. _Static анализ")
            print(f"{'─'*60}")

            report_static = []
            report_static.append(f"{'═'*60}")
            report_static.append(f"ШКАФ: {cabinet} — _Static точки")
            report_static.append(f"{'═'*60}")

            total_static = sum(len(v) for v in static_details.values())
            in_dpl_count = 0
            not_in_dpl_count = 0

            for struct in sorted(static_details.keys()):
                items = static_details[struct]
                base_type = struct.replace("_Static", "").replace("VZZDR", "VZZD")

                report_static.append(f"\n{'─'*60}")
                report_static.append(f"  {struct} ({len(items)} точек)")
                report_static.append(f"  Базовый DPL-тип: {base_type}")
                report_static.append(f"{'─'*60}")

                # На каких мнемосхемах
                mnemos_used: set[str] = set()
                for _, _, csv_f in items:
                    mnemos_used.add(csv_f.replace(".csv", ""))
                report_static.append(f"  Мнемосхемы: {', '.join(sorted(mnemos_used))}")

                # Есть ли в DPL
                report_static.append("")
                report_static.append(
                    f"  {'DP':<55s} {'В DPL?':<8s} {'DPL-тип':<20s} Описание"
                )
                report_static.append(
                    f"  {'─'*53} {'─'*6} {'─'*18} {'─'*30}"
                )

                for dp, desc, csv_f in sorted(items, key=lambda x: x[0]):
                    if dp in dpl_instances:
                        in_dpl_count += 1
                        dpl_t = dpl_instances[dp]
                        match_tag = "✅" if dpl_t == base_type else f"⚠ {dpl_t}"
                        report_static.append(
                            f"  {dp:<55s} {'да':<8s} {match_tag:<20s} {desc}"
                        )
                    else:
                        not_in_dpl_count += 1
                        report_static.append(
                            f"  {dp:<55s} {'НЕТ':<8s} {'—':<20s} {desc}"
                        )

            report_static.insert(3, f"  Всего _Static точек: {total_static}")
            report_static.insert(4, f"  Есть в DPL:          {in_dpl_count}")
            report_static.insert(5, f"  Нет в DPL:           {not_in_dpl_count}")

            print(f"  _Static типов:   {len(static_details)}")
            print(f"  Всего точек:     {total_static}")
            print(f"  Есть в DPL:      {in_dpl_count}")
            print(f"  Нет в DPL:       {not_in_dpl_count}")

            f4 = REPORT_DIR / f"{cabinet}_static_analysis.txt"
            f4.write_text("\n".join(report_static), encoding="utf-8")
            print(f"  → {f4.name}")

    print(f"\n{'═'*70}")
    print(f" Отчёты сохранены в {REPORT_DIR}")
    print(f"{'═'*70}")


if __name__ == "__main__":
    main()
