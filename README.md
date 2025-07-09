# PDF Cutoff List Extractor

## Overview

This project contains a Python script (`extract_first_page.py`) designed to extract data from specific PDF files, initially focused on the "2024-Cutoff-Maharashtra.pdf". It parses college and course cutoff information, including different levels (State Level, Home University, etc.) and stages (Stage I, Stage II) of data.

The script can process a specified number of pages from the PDF and outputs the extracted data into a CSV file.

## Requirements

- Python 3.x
- PyPDF2 (specified in `requirements.txt`)

## Setup

1.  Clone the repository (if applicable).
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

To run the PDF extraction script:

```bash
python extract_first_page.py
```

By default, when run directly as `__main__`, the script is configured to:
- Process the first 17 pages of "2024-Cutoff-Maharashtra.pdf".
- Save the output to `output_first_17_pages.csv`.

The number of pages to process and the output filename can be adjusted by modifying the variables in the `if __name__ == "__main__":` block within `extract_first_page.py`. The core extraction function `extract_first_page_content(pdf_path, output_csv_path, max_pages_to_process=1)` can also be imported and used in other Python scripts.

## Testing

A unit test suite is provided to verify the extraction logic for the first page of the PDF.

To run the tests:

```bash
python -m unittest test-first-page-extraction.py
```

The test compares the output of extracting the first page against a standard expected CSV output (`standard_expected_first_page_output.csv`).

## Structure

-   `extract_first_page.py`: The main script for PDF data extraction.
-   `test-first-page-extraction.py`: Unit test script for the first-page extraction functionality.
-   `standard_expected_first_page_output.csv`: The expected CSV output for the first page, used by the unit test.
-   `2024-Cutoff-Maharashtra.pdf`: The sample PDF document for extraction.
-   `.gitignore`: Specifies intentionally untracked files that Git should ignore.
-   `requirements.txt`: Lists project dependencies.
