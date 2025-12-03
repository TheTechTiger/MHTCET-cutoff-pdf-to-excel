import csv
import logging
import os
import re
from hashlib import md5
from pathlib import Path

import click
import pdfplumber
import PyPDF2

# ------------------------------------------------------------------------------
# Regex patterns
# ------------------------------------------------------------------------------

COLLEGE_RE = re.compile(r"(\d{5})\s*-\s*(.+)")
COURSE_RE = re.compile(r"(\d{10})\s*-\s*(.+)")
STATUS_RE = re.compile(r"Status:\s*(.+)")
RANK_PERC_RE = re.compile(r"(\d+)\s*\(([\d.]+)\)")

LEVEL_PATTERNS = [
    re.compile(p, re.I)
    for p in (
        r"Home University Seats Allotted to Home University Candidates",
        r"Other Than Home University Seats Allotted to Other Than Home University Candidates",
        r"Home University Seats Allotted to Other Than Home University Candidates",
        r"State Level",
        r"Maharashtra State Seats",
    )
]

SKIP_LINES = {
    "D",
    "i",
    "rState Common Entrance Test Cell",
    "Cut Off List for Maharashtra & Minority Seats of CAP Round I  for Admission to First Year of Four Year",
    "Degree Courses In Engineering and Technology & Master of Engineering and Technology (Integrated 5 Years ) for the Year 2024-25Government of Maharashtra",
    "Stage",
    "Legends: Starting character G-General, L-Ladies, End character H-Home University, O-Other than Home University,S-State Level, AI- All India Seat.",
    "Maharashtra State Seats - Cut Off Indicates Maharashtra State General Merit No.; Figures in bracket Indicates Merit Percentile.",
}

# ------------------------------------------------------------------------------
# Utility Functions
# ------------------------------------------------------------------------------

def table_fingerprint(table_rows: list[list[str | None]]) -> str:
    """Generate a stable MD5 hash of the first two non-empty rows of a table."""
    key = []
    for row in table_rows[:2]:
        if any(cell not in (None, "") for cell in row):
            key.append(tuple((cell or "").strip() for cell in row))
    digest = md5(str(tuple(key)).encode()).hexdigest()
    return digest

def configure_logging(log_file: Path) -> None:
    """Configure logging for the current extraction session."""
    logging.basicConfig(
        filename=str(log_file),
        level=logging.INFO,
        format="%(asctime)s – %(levelname)s – %(message)s",
        filemode="w",
    )

def write_csv(output_csv: Path, header: list[str], rows: list[list[str]]) -> None:
    """Write the extracted data rows to a CSV file."""
    with open(output_csv, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)

# ------------------------------------------------------------------------------
# Table Processing Logic
# ------------------------------------------------------------------------------

def _process_table(
    table: list[list[str | None]],
    header_cols: list[str],
    out_rows: list[list[str]],
    serial_start: int,
    page_num: int,
    college_code: str,
    college_name: str,
    course_code: str,
    course_name: str,
    status: str,
    level: str,
) -> int:
    """Process a single table and extract rank/percentile rows."""
    serial = serial_start
    table = [r for r in table if any(c not in (None, "") for c in r)]
    if not table:
        return serial

    header_row = table[0]
    if (
        len(header_row) < 2
        or not any(re.search(r"[A-Za-z]", str(c or "")) for c in header_row)
    ):
        logging.debug("Page %d: unable to identify header row, skipping table", page_num)
        return serial

    header_norm = [" ".join(str(c or "").split()) for c in header_row]
    category_offset = 1 if header_norm[0].upper() in {"STAGE", ""} else 0

    for row in table[1:]:
        cells = [" ".join(str(c or "").split()) for c in row]
        if not cells or not any(cells):
            continue
        stage = cells[0].upper()
        for idx, cell in enumerate(cells[1:], start=1):
            if not cell or cell == "-":
                continue
            m = RANK_PERC_RE.search(cell)
            if not m:
                continue
            rank, perc = m.groups()
            hdr_idx = idx - 1 + category_offset
            if hdr_idx >= len(header_norm):
                continue
            category = header_norm[hdr_idx]
            serial += 1
            out_rows.append([
                str(serial),
                str(page_num),
                college_code,
                college_name,
                course_code,
                course_name,
                status,
                level,
                stage,
                category,
                rank,
                perc,
            ])
    return serial

# ------------------------------------------------------------------------------
# PDF Extraction Core Logic
# ------------------------------------------------------------------------------

def extract_data_from_pdf(pdf_path: Path, output_csv: Path, log_file: Path, max_pages: int | None = None) -> None:
    """
    Main function to extract tabular data from a structured PDF and output CSV.
    """
    configure_logging(log_file)

    header = [
        "Sr. No.",
        "Page",
        "College Code",
        "College Name",
        "Course Code",
        "Course Name",
        "Status",
        "Level",
        "Stage",
        "Caste/Category",
        "Cut‑off Rank",
        "Cut‑off Percentile",
    ]
    rows: list[list[str]] = []
    serial = 0

    try:
        with pdfplumber.open(pdf_path) as pl, open(pdf_path, "rb") as fh:
            reader = PyPDF2.PdfReader(fh)
            n_pages = len(pl.pages)
            if n_pages == 0:
                logging.error("PDF has no pages – aborting.")
                raise ValueError("No pages in PDF")

            pages_to_process = n_pages if max_pages is None else min(max_pages, n_pages)
            logging.info("Processing %s / %s pages", pages_to_process, n_pages)

            seen_tables: set[str] = set()
            current_level = "State Level"
            current_college_code = current_college_name = ""
            current_course_code = current_course_name = ""
            current_status = ""

            for pg in range(pages_to_process):
                page_num = pg + 1
                logging.info("— Page %d —", page_num)
                pypdf_text = reader.pages[pg].extract_text() or ""
                lines = [ln.strip() for ln in pypdf_text.split("\n") if ln.strip() and ln.strip() not in SKIP_LINES]

                plumber_page = pl.pages[pg]
                all_tables = plumber_page.extract_tables() or []
                table_cursor = 0

                line_idx = 0
                while line_idx < len(lines):
                    ln = lines[line_idx]
                    for lvl_re in LEVEL_PATTERNS:
                        if lvl_re.search(ln):
                            current_level = " ".join(lvl_re.pattern.split())
                            logging.info("Page %d: Level ➜ %s", page_num, current_level)
                            if table_cursor < len(all_tables):
                                tbl = all_tables[table_cursor]
                                table_cursor += 1
                                fp = table_fingerprint(tbl)
                                if fp in seen_tables:
                                    logging.debug("Page %d: duplicate table skipped", page_num)
                                    break
                                seen_tables.add(fp)
                                serial = _process_table(
                                    tbl, header, rows, serial, page_num,
                                    current_college_code, current_college_name,
                                    current_course_code, current_course_name,
                                    current_status, current_level
                                )
                            break
                    else:
                        if (m := COLLEGE_RE.match(ln)):
                            current_college_code, current_college_name = m.groups()
                            logging.info("Page %d: College ➜ %s – %s", page_num, current_college_code, current_college_name)
                            current_course_code = current_course_name = current_status = ""
                        elif (m := COURSE_RE.match(ln)):
                            current_course_code, current_course_name = m.groups()
                            logging.info("Page %d: Course ➜ %s – %s", page_num, current_course_code, current_course_name)
                            if line_idx + 1 < len(lines) and (m2 := STATUS_RE.match(lines[line_idx + 1])):
                                current_status = " ".join(m2.group(1).split())
                                line_idx += 1
                                logging.info("Page %d: Status ➜ %s", page_num, current_status)
                    line_idx += 1

    except FileNotFoundError:
        logging.error("PDF file not found: %s", pdf_path)
    except Exception as exc:
        logging.exception("Unexpected error: %s", exc)

    write_csv(output_csv, header, rows)
    print(f"✔ Extraction finished – {len(rows)} rows written to {output_csv}")

# ------------------------------------------------------------------------------
# Directory Traversal
# ------------------------------------------------------------------------------

def process_folder(folder: Path, max_pages: int | None = None) -> None:
    """
    Recursively traverse folder for PDFs and extract tables into CSVs and logs.
    """
    for path in folder.rglob("*.pdf"):
        output_csv = path.with_suffix(".csv")
        log_file = path.with_name(path.stem + ".log")
        print(f"→ Processing: {path}")
        extract_data_from_pdf(path, output_csv, log_file, max_pages)

# ------------------------------------------------------------------------------
# Click CLI Interface
# ------------------------------------------------------------------------------

@click.command()
@click.argument("folder", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--max-pages", "-n", type=int, default=None, help="Maximum number of pages to process per PDF.")
def main(folder: Path, max_pages: int | None) -> None:
    """Extract admission cutoff data from all PDFs in the FOLDER recursively."""
    process_folder(folder, max_pages)

if __name__ == "__main__":
    main()
