"""
Проверка переводов строк во всех XML файлах.
Показывает сколько файлов CRLF, LF, и смешанных.
"""

from pathlib import Path
from parse_utils import PANELS_DIR, OBJECTS_DIR, VISION_DIR, REPORT_DIR

REPORT_FILE = REPORT_DIR / "line_endings_check.txt"


def check_file(f: Path) -> str:
    raw = f.read_bytes()
    has_crlf = b'\r\n' in raw
    lf_only = raw.count(b'\n') - raw.count(b'\r\n')
    if has_crlf and lf_only > 0:
        return "MIXED"
    elif has_crlf:
        return "CRLF"
    elif lf_only > 0:
        return "LF"
    return "NONE"


def main():
    stats = {"CRLF": [], "LF": [], "MIXED": [], "NONE": []}

    scan_dirs = []
    if OBJECTS_DIR.exists():
        scan_dirs.append(OBJECTS_DIR)
    if VISION_DIR.exists():
        scan_dirs.append(VISION_DIR)

    for scan_dir in scan_dirs:
        for xml_file in sorted(scan_dir.rglob("*.xml")):
            result = check_file(xml_file)
            rel = str(xml_file.relative_to(PANELS_DIR)).replace("\\", "/")
            stats[result].append(rel)

    report: list[str] = []
    report.append("Проверка переводов строк в XML файлах")
    report.append("=" * 60)
    report.append(f"LF (Unix):    {len(stats['LF'])}")
    report.append(f"CRLF (Win):   {len(stats['CRLF'])}")
    report.append(f"MIXED:        {len(stats['MIXED'])}")
    report.append(f"Нет переносов: {len(stats['NONE'])}")
    report.append("")

    if stats["CRLF"]:
        report.append("Файлы с CRLF (первые 20):")
        for f in stats["CRLF"][:20]:
            report.append(f"  {f}")
        if len(stats["CRLF"]) > 20:
            report.append(f"  ... и ещё {len(stats['CRLF']) - 20}")
        report.append("")

    if stats["MIXED"]:
        report.append("Файлы со смешанными переносами:")
        for f in stats["MIXED"]:
            report.append(f"  {f}")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(report) + "\n")

    print("\n".join(report))
    print(f"\nОтчёт: {REPORT_FILE}")


if __name__ == "__main__":
    main()
