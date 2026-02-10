"""
Скрипт для конвертации CRLF → LF в сгенерированных .ctl файлах.

Результат: fix_lf_report.txt
"""

from pathlib import Path
from parse_utils import CTL_DIR, REPORT_DIR

SCRIPTS_DIR = CTL_DIR
REPORT_FILE = REPORT_DIR / "fix_lf_report.txt"


def main():
    if not SCRIPTS_DIR.exists():
        print(f"Папка не найдена: {SCRIPTS_DIR}")
        return

    ctl_files = sorted(SCRIPTS_DIR.glob("Ventcontent_*.ctl"))
    if not ctl_files:
        print("Файлы Ventcontent_*.ctl не найдены.")
        return

    fixed = 0
    skipped = 0
    report_lines: list[str] = []

    for f in ctl_files:
        raw = f.read_bytes()
        if b'\r\n' in raw:
            new_raw = raw.replace(b'\r\n', b'\n')
            f.write_bytes(new_raw)
            fixed += 1
            report_lines.append(f"  [✓] {f.name}")
        else:
            skipped += 1

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    with open(REPORT_FILE, "w", encoding="utf-8") as rf:
        rf.write(f"Исправлено: {fixed}\nПропущено (уже LF): {skipped}\n\n")
        rf.write("\n".join(report_lines) + "\n")

    print(f"Исправлено: {fixed}, уже LF: {skipped}")
    print(f"Отчёт: {REPORT_FILE}")


if __name__ == "__main__":
    main()
