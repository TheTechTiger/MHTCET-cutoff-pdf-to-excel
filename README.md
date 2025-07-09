# PDF Cutoff List Extractor

## Overview

This project contains a Python script (`data_extractor.py`) designed to extract data from specific PDF files, such as "2024-Cutoff-Maharashtra.pdf". It parses college and course cutoff information, including different 'Level' headers (e.g., State Level, Home University Seats Allotted to Home University Candidates) and data Stages (Stage I, Stage II).

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
python data_extractor.py
```

By default, when run directly as `__main__`, the `data_extractor.py` script is configured to:
- Process the first 17 pages of "2024-Cutoff-Maharashtra.pdf".
- Save the output to `standalone_17_page_run_output.csv` (this file is gitignored).

The number of pages to process and the output filename for direct execution can be adjusted by modifying the variables in the `if __name__ == "__main__":` block within `data_extractor.py`. The core extraction function `extract_data_from_pdf(pdf_path, output_csv_path, max_pages_to_process=1)` can also be imported and used in other Python scripts.

## Testing

A unit test suite is provided to verify the extraction logic for the first 17 pages of the PDF.

To run the tests:

```bash
python -m unittest test_data_extraction.py
```

The test compares the output of extracting 17 pages against a standard expected CSV output (`expected_17_page_output.csv`).

## Structure

-   `data_extractor.py`: The main script for PDF data extraction.
-   `test_data_extraction.py`: Unit test script for the 17-page data extraction.
-   `expected_17_page_output.csv`: The expected CSV output for the first 17 pages, used by the unit test.
-   `2024-Cutoff-Maharashtra.pdf`: The sample PDF document for extraction.
-   `.gitignore`: Specifies intentionally untracked files that Git should ignore.
-   `requirements.txt`: Lists project dependencies.
