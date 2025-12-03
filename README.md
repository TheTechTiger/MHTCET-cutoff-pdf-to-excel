# CET PDF Data Extractor

This script, `cet_2024.py`, is designed to extract tabular data from PDF files, specifically targeting Maharashtra CET (Common Entrance Test) cut-off list **(only Maharashtra Level)** documents. It recursively searches a given folder for PDF files, processes each one, and outputs the extracted data into a CSV file and a log file, both named after the original PDF and saved in the same directory as the PDF.

## Features

*   **Recursive PDF Discovery:** Scans a specified root folder and all its subdirectories for `.pdf` files.
*   **Data Extraction:** Parses text and tables from PDFs to find and extract college admission cut-off data, including college codes, course names, categories, ranks, and percentiles.
*   **Individual CSV Output:** For each processed PDF, a corresponding CSV file is generated (e.g., `source.pdf` -> `source.csv`).
*   **Individual Log Output:** For each processed PDF, a log file detailing the extraction process is generated (e.g., `source.pdf` -> `source.log`).
*   **Duplicate Table Handling:** Identifies and skips processing of duplicate tables within a PDF to ensure data integrity.

## Prerequisites

Before running the script, ensure you have Python 3 installed. The necessary Python libraries are listed in `requirements.txt`.

## Installation

1.  Clone this repository or download the script and `requirements.txt`.
2.  Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

To run the script, execute `cet_2024.py` from your terminal, providing the path to the folder containing the PDF files you want to process.

```bash
python cet_2024.py /path/to/your/pdf_folder/
```

**Optional Argument:**

You can also specify the maximum number of pages to process for each PDF. This can be useful for testing or if you only need data from the beginning of large documents.

```bash
python cet_2024.py /path/to/your/pdf_folder/ [max_pages]
```
For example, to process only the first 5 pages of each PDF:
```bash
python cet_2024.py /path/to/your/pdf_folder/ 5
```

## Input

*   **Folder Path (required):** The path to the directory where the script will start its recursive search for PDF files.
*   **Max Pages (optional):** An integer specifying the maximum number of pages to process per PDF. If omitted, all pages are processed.

## Output

For each PDF file found (e.g., `example_document.pdf`) in the input folder or its subdirectories, the script will generate two files in the *same directory as the PDF*:

1.  **CSV File (`example_document.csv`):** Contains the extracted tabular data with the following columns:
    *   `Sr. No.`
    *   `Page`
    *   `College Code`
    *   `College Name`
    *   `Course Code`
    *   `Course Name`
    *   `Status`
    *   `Level`
    *   `Stage`
    *   `Caste/Category`
    *   `Cut‑off Rank`
    *   `Cut‑off Percentile`
2.  **Log File (`example_document.log`):** Contains logging information about the extraction process for that specific PDF, including processed pages, identified colleges/courses, and any errors or warnings encountered.

## How it Works

The script uses the `pdfplumber` and `PyPDF2` libraries to open and read PDF files. It iterates through pages, extracting text lines and tables. Regular expressions are used to identify key information such as college details, course details, admission status, and cut-off levels.

A fingerprinting mechanism for tables helps in avoiding the processing of redundant table data that might appear multiple times (e.g., headers repeated on new pages without actual new data rows immediately following).

The extracted data is then structured and written to a CSV file, and operational logs are saved to a corresponding log file.
