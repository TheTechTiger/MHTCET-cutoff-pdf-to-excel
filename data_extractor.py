import PyPDF2 # Still used for page count and initial page object
import pdfplumber # New library for table extraction
import re
import logging
import csv
import os

logging.basicConfig(filename='data_extraction.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s', filemode='w')

# This regex will still be used for parsing rank/percentile from table cells
rank_percentile_re = re.compile(r"(\d+)\s*\(([\d.]+)\)")

def extract_data_from_pdf(pdf_path, output_csv_path, max_pages_to_process=1):
    logging.info(f"Starting PDF data extraction from: {pdf_path} for {max_pages_to_process} page(s) using PDFPlumber strategy.")
    logging.info(f"Output will be written to: {output_csv_path}")

    extracted_data_rows = []
    serial_number = 0
    header = ["Sr. No.","Page Number","College Code","College Name","Course Code","Course Name","Status","Level","Stage","Caste_Category","Cutoff Rank","Cutoff Percentile"]

    try:
        with pdfplumber.open(pdf_path) as pdf, open(pdf_path, 'rb') as f_pdf_pypdf2: # Open with PyPDF2 for page text
            # PyPDF2 for page text needed for context headers (college, course, etc.)
            reader_pypdf2 = PyPDF2.PdfReader(f_pdf_pypdf2)
            num_actual_pages = len(pdf.pages) # Use pdfplumber for actual page count

            if num_actual_pages == 0:
                logging.warning("The PDF file has no pages.")
                with open(output_csv_path, 'w', newline='', encoding='utf-8') as csv_file:
                    csv_writer = csv.writer(csv_file)
                    csv_writer.writerow(header)
                return

            pages_to_process_actually = min(max_pages_to_process, num_actual_pages)
            logging.info(f"Will process {pages_to_process_actually} page(s) out of {num_actual_pages} actual pages.")

            current_college_code = ""
            current_college_name = ""
            current_course_code = ""
            current_course_name = ""
            current_status = ""
            current_level = "State Level"

            # Regex for context (outside table) - still needed
            college_re = re.compile(r"(\d{5})\s*-\s*(.+)")
            course_re = re.compile(r"(\d{10})\s*-\s*(.+)")
            status_re = re.compile(r"Status:\s*(.+)")

            level_patterns = [
                re.compile(r"Home University Seats Allotted to Home University Candidates", re.IGNORECASE),
                re.compile(r"Other Than Home University Seats Allotted to Other Than Home University Candidates", re.IGNORECASE),
                re.compile(r"Home University Seats Allotted to Other Than Home University Candidates", re.IGNORECASE),
                re.compile(r"State Level", re.IGNORECASE),
                re.compile(r"Maharashtra State Seats", re.IGNORECASE),
                re.compile(r"Home University", re.IGNORECASE),
                re.compile(r"Other Than Home University", re.IGNORECASE),
            ]

            skip_these_exact_lines = [ # These are for the PyPDF2 text processing part
                "D", "i", "rState Common Entrance Test Cell",
                "Cut Off List for Maharashtra & Minority Seats of CAP Round I  for Admission to First Year of Four Year",
                "Degree Courses In Engineering and Technology & Master of Engineering and Technology (Integrated 5 Years ) for the Year 2024-25Government of Maharashtra",
                "Stage",
                "Legends: Starting character G-General, L-Ladies, End character H-Home University, O-Other than Home University,S-State Level, AI- All India Seat.",
                "Maharashtra State Seats - Cut Off Indicates Maharashtra State General Merit No.; Figures in bracket Indicates Merit Percentile."
            ]

            for page_idx in range(pages_to_process_actually):
                current_page_num = page_idx + 1
                logging.info(f"Processing Page: {current_page_num}")

                # Use PyPDF2 for extracting full page text for context headers
                pypdf2_page = reader_pypdf2.pages[page_idx]
                page_text_for_context = pypdf2_page.extract_text()

                if not page_text_for_context:
                    logging.warning(f"Could not extract any text using PyPDF2 from page {current_page_num} for context.")
                    # We might still proceed if pdfplumber can get tables, but context will be weak.

                lines_for_context = page_text_for_context.split('\n') if page_text_for_context else []

                # Reset per-page context, but try to carry over from previous if not found on current page.
                # This simplistic carry-over might need refinement.
                # For now, we assume college/course info is usually found before tables they apply to on a page.

                # --- Existing Regex Logic for College/Course/Status/Level Headers ---
                # (This part remains largely the same, using lines_for_context)
                temp_line_idx = 0
                # Try to find the most recent College/Course/Status/Level before table parsing
                # This is a simplified context grabber; might need to be more sophisticated
                # to associate with specific tables if multiple courses/colleges on one page.

                # Reset for current page context finding pass
                page_specific_college_code = ""
                page_specific_college_name = ""
                page_specific_course_code = ""
                page_specific_course_name = ""
                page_specific_status = ""
                # current_level is carried over or reset to default if not found

                for line_idx_ctx, line_ctx_content in enumerate(lines_for_context):
                    line_ctx = line_ctx_content.strip()
                    if not line_ctx or line_ctx in skip_these_exact_lines:
                        continue

                    level_header_found_on_page = False
                    for level_re_pattern in level_patterns:
                        level_match = level_re_pattern.search(line_ctx)
                        if level_match:
                            matched_level_text = level_match.group(0).strip()
                            current_level = " ".join(matched_level_text.split())
                            logging.info(f"Page {current_page_num}: Updated Level (from PyPDF2 text) to: {current_level}")
                            level_header_found_on_page = True
                            break
                    if level_header_found_on_page: continue

                    college_match = college_re.match(line_ctx)
                    if college_match:
                        current_college_code = college_match.group(1)
                        college_name_str = college_match.group(2).strip().replace('\n', ' ').replace('\r', ' ')
                        current_college_name = " ".join(college_name_str.split())
                        logging.info(f"Page {current_page_num}: Matched College (from PyPDF2 text): {current_college_code} - {current_college_name}")
                        # Once a college is found, subsequent course applies to it until new college
                        current_course_code = ""
                        current_course_name = ""
                        current_status = ""
                        continue

                    course_match = course_re.match(line_ctx)
                    if course_match and current_college_code: # Course should belong to a college
                        current_course_code = course_match.group(1)
                        course_name_str = course_match.group(2).strip().replace('\n', ' ').replace('\r', ' ')
                        current_course_name = " ".join(course_name_str.split())
                        logging.info(f"Page {current_page_num}: Matched Course (from PyPDF2 text): {current_course_code} - {current_course_name}")
                        current_status = "" # Reset status for new course

                        # Check for status on the next line
                        if line_idx_ctx + 1 < len(lines_for_context):
                            status_line = lines_for_context[line_idx_ctx + 1].strip()
                            status_match = status_re.match(status_line)
                            if status_match:
                                status_str = status_match.group(1).strip().replace('\n', ' ').replace('\r', ' ')
                                current_status = " ".join(status_str.split())
                                logging.info(f"Page {current_page_num}: Matched Status (from PyPDF2 text): {current_status}")
                        else:
                             logging.warning(f"Page {current_page_num}: No line after course for status check.")

                        # --- PDFPlumber Table Extraction and Processing for this Course context ---
                        # This is where the new logic will go, after a course is identified.
                        # The current_college_*, current_course_*, current_status, current_level are now set.

                        # Get the pdfplumber page object
                        plumber_page = pdf.pages[page_idx]
                        # Extract tables using pdfplumber
                        # TODO: Potentially refine table extraction settings based on exploration
                        tables = plumber_page.extract_tables()

                        if tables:
                            logging.info(f"Page {current_page_num}: PDFPlumber found {len(tables)} tables for course {current_course_name}.")
                            # The actual processing of these tables will be in the next plan step.
                            # For now, just log that they were found.
                            # Placeholder for table processing logic:
                            for table_idx, table_data in enumerate(tables):
                                logging.info(f"  Processing PDFPlumber table {table_idx + 1} on page {current_page_num} for course {current_course_name}")
                                if not table_data:
                                    logging.warning(f"    Table {table_idx+1} is empty.")
                                    continue

                                # Attempt to identify the header row (categories)
                                # A simple heuristic: first row with multiple non-None, non-empty strings,
                                # and not starting with typical stage markers like "I" or "II".
                                header_row_data = []
                                data_row_start_index = 0

                                # Clean table_data: remove rows that are all None or all empty strings
                                cleaned_table_data = [r for r in table_data if not all(cell is None or cell == '' for cell in r)]
                                if not cleaned_table_data:
                                    logging.warning(f"    Table {table_idx+1} is empty after cleaning.")
                                    continue

                                # Try to find header row (usually the first row in cleaned data)
                                potential_header_row = cleaned_table_data[0]
                                first_cell_hdr_content = str(potential_header_row[0]).strip().upper() if potential_header_row[0] is not None else ""

                                looks_like_header = True
                                # Condition 1: First cell should not be 'I' or 'II' (typical stage markers for data rows)
                                if first_cell_hdr_content in ["I", "II"]:
                                    looks_like_header = False

                                # Condition 2: Must have at least two columns for a meaningful header (Stage/None + Category)
                                if len(potential_header_row) < 2:
                                    looks_like_header = False

                                # Condition 3: If it looks like a header so far, check content of second cell.
                                # It should look like a category name (text) not rank/percentile data or purely numeric.
                                if looks_like_header:
                                    second_cell_hdr_content = str(potential_header_row[1]).strip() if potential_header_row[1] is not None else ""
                                    if not second_cell_hdr_content: # Second cell (first category) shouldn't be empty
                                        looks_like_header = False
                                    elif rank_percentile_re.search(second_cell_hdr_content) or second_cell_hdr_content.isdigit():
                                        looks_like_header = False # Looks like data, not a category name
                                    # Further check: ensure it contains some alphabetic characters (common for category codes)
                                    elif not re.search(r"[a-zA-Z]", second_cell_hdr_content):
                                        looks_like_header = False


                                if looks_like_header:
                                    header_row_data = [str(cell).strip().replace('\n',' ') if cell is not None else "" for cell in potential_header_row]
                                    data_row_start_index = 1
                                    logging.info(f"    Identified Header Row: {header_row_data}")
                                else:
                                    logging.warning(f"    Skipping table {table_idx+1} on page {current_page_num}: Could not identify a clear header row. First row: {potential_header_row}")
                                    continue

                                if not header_row_data: # Should not happen if looks_like_header is True and logic is correct
                                    logging.error(f"    Internal error: Header row data is empty for table {table_idx+1} despite passing checks. Skipping.")
                                    continue

                                # Process data rows
                                for r_idx in range(data_row_start_index, len(cleaned_table_data)):
                                    data_row = cleaned_table_data[r_idx]
                                    data_row_cleaned = [str(cell).strip().replace('\n', ' ') if cell is not None else "" for cell in data_row]

                                    if not data_row_cleaned or not any(data_row_cleaned): # Skip if row is effectively empty
                                        continue

                                    stage_from_cell = data_row_cleaned[0].upper() # Expect 'I' or 'II'
                                    if stage_from_cell not in ["I", "II"]:
                                        # This might be a continuation line within a stage, or a malformed row.
                                        # For now, we require an explicit Stage marker in the first column of a data row.
                                        logging.debug(f"    Skipping data row {r_idx} in table {table_idx+1} as first cell '{stage_from_cell}' is not 'I' or 'II'. Row: {data_row_cleaned}")
                                        continue

                                    logging.info(f"    Processing Data Row (Stage {stage_from_cell}): {data_row_cleaned}")

                                    # Iterate through cells of this data row, aligning with header categories
                                    # Start from index 1 in data_row_cleaned because index 0 is the Stage
                                    # Start from index 1 in header_row_data if its first cell was 'Stage' or similar,
                                    # otherwise start from 0 if it was just categories.
                                    # A common pattern is header_row_data[0] is None or "Stage", so categories start at header_row_data[1]

                                    category_offset = 0
                                    if header_row_data[0].upper() == "STAGE" or header_row_data[0] == "":
                                        category_offset = 1

                                    for cell_idx in range(1, len(data_row_cleaned)):
                                        cell_data_str = data_row_cleaned[cell_idx]

                                        header_col_idx = cell_idx - 1 + category_offset # Align data cell with category header cell
                                        if header_col_idx < len(header_row_data):
                                            category_name = header_row_data[header_col_idx]
                                            if not category_name: # Skip if category name in header is empty
                                                continue
                                        else:
                                            logging.warning(f"      Ran out of headers for cell_idx {cell_idx}, header_col_idx {header_col_idx}. Header len: {len(header_row_data)}")
                                            continue # Skip if no corresponding header

                                        if cell_data_str: # If there's data in the cell
                                            rp_match = rank_percentile_re.search(cell_data_str)
                                            if rp_match:
                                                rank, percentile = rp_match.groups()
                                                serial_number += 1
                                                output_row = [
                                                    str(serial_number), str(current_page_num),
                                                    current_college_code, current_college_name,
                                                    current_course_code, current_course_name,
                                                    current_status, current_level,
                                                    stage_from_cell, category_name, rank, percentile
                                                ]
                                                extracted_data_rows.append(output_row)
                                                logging.debug(f"      Extracted: {output_row}")
                                            elif cell_data_str.strip() != '-': # '-' often means 'no data' but not empty
                                                logging.debug(f"      Cell '{cell_data_str}' for category '{category_name}' in Stage '{stage_from_cell}' did not match R/P pattern and is not just '-'.")
                                        # else: cell is empty, means no data for this category/stage, so skip
                            # --- End of PDFPlumber Table Processing ---
                        else:
                            logging.warning(f"Page {current_page_num}: PDFPlumber found NO tables for course {current_course_name} (or on page generally after this context).")

                        # After processing tables for this course, the regex loop will continue and potentially find another course on the same page.
                        # Context (college, course, status, level) should be valid for tables found *after* these headers
                        # and *before* new headers are encountered. This implicit association is a potential weak point.
                        continue # To the main line processing loop (while line_idx < len(lines)) to find next college/course on the page

                    # If not a college, not a course (that we could process), and not a level header (handled at top of loop)
                # End of line_idx_ctx loop for context headers

            # End of per-page processing loop (PyPDF2/PDFPlumber combined)

    except FileNotFoundError:
        logging.error(f"Error: The PDF file '{pdf_path}' was not found.")
        print(f"Error: The PDF file '{pdf_path}' was not found.")
        with open(output_csv_path, 'w', newline='', encoding='utf-8') as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow(header)
        return
    except Exception as e:
        logging.error(f"An unexpected error occurred during regex parsing: {e}", exc_info=True)
        print(f"An unexpected error occurred: {e}")
        with open(output_csv_path, 'w', newline='', encoding='utf-8') as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow(header)
        return

    with open(output_csv_path, 'w', newline='', encoding='utf-8') as csv_file:
        csv_writer = csv.writer(csv_file, lineterminator='\n')
        csv_writer.writerow(header)
        if extracted_data_rows:
            csv_writer.writerows(extracted_data_rows)
            logging.info(f"--- Finished regex-based processing. {len(extracted_data_rows)} rows saved to {output_csv_path} ---")
            print(f"Regex-based extraction complete. {len(extracted_data_rows)} rows saved to '{output_csv_path}'.")
        else:
            logging.warning("No data was extracted using regex logic.")
            print(f"No data extracted. Empty CSV with header saved to '{output_csv_path}'.")

if __name__ == "__main__":
    pdf_file_path_main = "2024-Cutoff-Maharashtra.pdf"
    output_csv_path_main = "standalone_17_page_run_output.csv" # New distinct output for direct runs
    num_pages_to_process_main = 17 # RESTORED FOR FULL 17-PAGE RUN

    if not os.path.exists(pdf_file_path_main):
        print(f"PDF file not found: {pdf_file_path_main}")
    else:
        extract_data_from_pdf(pdf_file_path_main, output_csv_path_main, max_pages_to_process=num_pages_to_process_main) # Use new function name
        print(f"Standalone run for {num_pages_to_process_main} pages. Output to {output_csv_path_main}. Check data_extraction.log for details.")
