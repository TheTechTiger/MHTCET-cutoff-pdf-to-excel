import PyPDF2
import re
import logging
import csv
import os

logging.basicConfig(filename='first_page_extraction.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s', filemode='w')

def extract_first_page_content(pdf_path, output_csv_path, max_pages_to_process=1): # Added max_pages_to_process
    logging.info(f"Starting regex-based extraction from PDF: {pdf_path} for {max_pages_to_process} page(s).")
    logging.info(f"Output will be written to: {output_csv_path}")

    extracted_data_rows = []
    serial_number = 0
    header = ["Sr. No.","Page Number","College Code","College Name","Course Code","Course Name","Status","Level","Stage","Caste_Category","Cutoff Rank","Cutoff Percentile"]

    try:
        with open(pdf_path, 'rb') as f_pdf:
            reader = PyPDF2.PdfReader(f_pdf)
            num_actual_pages = len(reader.pages)

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
            current_level = "State Level" # Default, will be updated by dynamic level logic in next step

            # Define Regex patterns and skip lists once before the page loop
            college_re = re.compile(r"(\d{5})\s*-\s*(.+)")
            course_re = re.compile(r"(\d{10})\s*-\s*(.+)")
            status_re = re.compile(r"Status:\s*(.+)")
            rank_percentile_re = re.compile(r"(\d+)\s*\(([\d.]+)\)")
            data_line_detect_re = re.compile(r"^\s*I\s+(.*)")

            level_patterns = [
                # Order matters: more specific patterns first
                re.compile(r"Home University Seats Allotted to Home University Candidates", re.IGNORECASE),
                re.compile(r"Other Than Home University Seats Allotted to Other Than Home University Candidates", re.IGNORECASE),
                re.compile(r"Home University Seats Allotted to Other Than Home University Candidates", re.IGNORECASE), # From prompt, slight variation
                re.compile(r"State Level", re.IGNORECASE),
                re.compile(r"Maharashtra State Seats", re.IGNORECASE),
                # Shorter, more general patterns last to avoid premature matching
                re.compile(r"Home University", re.IGNORECASE),
                re.compile(r"Other Than Home University", re.IGNORECASE),
            ]

            skip_these_exact_lines = [
                "D", "i", "rState Common Entrance Test Cell",
                "Cut Off List for Maharashtra & Minority Seats of CAP Round I  for Admission to First Year of Four Year",
                "Degree Courses In Engineering and Technology & Master of Engineering and Technology (Integrated 5 Years ) for the Year 2024-25Government of Maharashtra",
                # "State Level", # This will be handled by dynamic level detection
                "Stage",
                "Legends: Starting character G-General, L-Ladies, End character H-Home University, O-Other than Home University,S-State Level, AI- All India Seat.",
                "Maharashtra State Seats - Cut Off Indicates Maharashtra State General Merit No.; Figures in bracket Indicates Merit Percentile."
            ]

            for page_idx in range(pages_to_process_actually):
                current_page_num = page_idx + 1
                logging.info(f"Processing Page: {current_page_num}")
                page = reader.pages[page_idx]
                page_text = page.extract_text()

                if not page_text:
                    logging.warning(f"Could not extract any text from page {current_page_num}.")
                    continue # Move to next page

                lines = page_text.split('\n')

                # Regex patterns are defined outside the page loop for efficiency, moved them up.
                # Make sure they are defined before this loop.

                # The rest of the parsing logic for a single page starts here
                line_idx = 0
                while line_idx < len(lines):
                    line = lines[line_idx].strip()

                    if not line or line in skip_these_exact_lines:
                        line_idx += 1
                        continue

                    # Check for Level headers FIRST
                    is_level_header = False
                    for level_re_pattern in level_patterns: # Renamed to avoid conflict
                        level_match = level_re_pattern.search(line)
                        if level_match:
                            matched_level_text = level_match.group(0).strip()
                            current_level = " ".join(matched_level_text.split()) # Normalize spaces
                            logging.info(f"Page {current_page_num}: Updated Level to: {current_level}")
                            line_idx += 1
                            is_level_header = True
                            break
                    if is_level_header:
                        continue

                    college_match = college_re.match(line)
                    if college_match:
                        current_college_code = college_match.group(1)
                        college_name_str = college_match.group(2).strip().replace('\n', ' ').replace('\r', ' ')
                        current_college_name = " ".join(college_name_str.split())
                        logging.info(f"Page {current_page_num}: Matched College: {current_college_code} - {current_college_name}")
                        line_idx += 1
                        continue

                    course_match = course_re.match(line)
                    if course_match and current_college_code:
                        current_course_code = course_match.group(1)
                        course_name_str = course_match.group(2).strip().replace('\n', ' ').replace('\r', ' ')
                        current_course_name = " ".join(course_name_str.split())
                        logging.info(f"Page {current_page_num}: Matched Course: {current_course_code} - {current_course_name}")

                        line_idx += 1
                        current_status = ""
                        if line_idx < len(lines):
                            status_line = lines[line_idx].strip()
                            status_match = status_re.match(status_line)
                            if status_match:
                                status_str = status_match.group(1).strip().replace('\n', ' ').replace('\r', ' ')
                                current_status = " ".join(status_str.split())
                                logging.info(f"Page {current_page_num}: Matched Status: {current_status}")
                                line_idx += 1
                            else:
                                logging.warning(f"Page {current_page_num}: Expected status line, found: {status_line} for course {current_course_name}")

                        # Loop for multiple Level/Data subsections within the current course
                        while True:
                            # Attempt to find a new Level header for this subsection
                            # The current_level from previous iterations or page headers is the default

                            # Check if the current line is a level header.
                            # This means a level header can appear directly before categories.
                            if line_idx < len(lines):
                                line_to_check_for_level = lines[line_idx].strip()
                                is_new_subsection_level = False
                                for level_re_pattern in level_patterns:
                                    level_match = level_re_pattern.search(line_to_check_for_level)
                                    if level_match and len(level_match.group(0)) > 0.7 * len(line_to_check_for_level): # Heuristic
                                        matched_level_text = level_match.group(0).strip()
                                        current_level = " ".join(matched_level_text.split())
                                        logging.info(f"Page {current_page_num}, Course {current_course_name}: Subsection Level updated to: {current_level}")
                                        line_idx += 1 # Consume this level line
                                        is_new_subsection_level = True
                                        break
                                # If it was a level line, line_idx is advanced. If not, line_idx is unchanged.

                            # Now, collect category codes
                            category_codes_text = ""
                            # Start collecting categories from the current line_idx
                            # Stop if we hit a data line, new college/course, known footer, or end of lines
                            temp_cat_line_idx = line_idx
                            while temp_cat_line_idx < len(lines):
                                potential_cat_line = lines[temp_cat_line_idx].strip()
                                if not potential_cat_line or \
                                   data_line_detect_re.match(potential_cat_line) or \
                                   college_re.match(potential_cat_line) or \
                                   course_re.match(potential_cat_line) or \
                                   status_re.match(potential_cat_line) or \
                                   potential_cat_line == "Stage" or \
                                   "Legends:" in potential_cat_line or \
                                   any(lp.search(potential_cat_line) for lp in level_patterns if len(lp.pattern) > 0.7 * len(potential_cat_line)) and temp_cat_line_idx > line_idx :
                                    break
                                category_codes_text += " " + potential_cat_line
                                temp_cat_line_idx += 1

                            # Only advance line_idx if categories were actually consumed
                            if temp_cat_line_idx > line_idx:
                                line_idx = temp_cat_line_idx

                            actual_category_codes = [code for code in category_codes_text.strip().split(' ') if code.isupper() and len(code)>1 and code != 'I']
                            logging.info(f"Page {current_page_num}, Course {current_course_name}, Level '{current_level}': Potential Categories: {actual_category_codes}")

                            # Collect data values
                            data_values_text = ""
                            if line_idx < len(lines):
                                initial_data_match = data_line_detect_re.match(lines[line_idx].strip())
                                if initial_data_match:
                                    data_values_text += " " + initial_data_match.group(1).strip()
                                    line_idx += 1
                                    while line_idx < len(lines): # Collect continuation data lines
                                        potential_data_continuation_line = lines[line_idx].strip()
                                        if potential_data_continuation_line and \
                                           re.search(r'[\d\.\(\)]', potential_data_continuation_line) and \
                                           not college_re.match(potential_data_continuation_line) and \
                                           not course_re.match(potential_data_continuation_line) and \
                                           not status_re.match(potential_data_continuation_line) and \
                                           not any(lp.search(potential_data_continuation_line) for lp in level_patterns if len(lp.pattern) > 0.7 * len(potential_data_continuation_line) ) and \
                                           potential_data_continuation_line != "Stage" and \
                                           "Legends:" not in potential_data_continuation_line:
                                            data_values_text += " " + potential_data_continuation_line
                                            line_idx += 1
                                        else:
                                            break
                                else: # No initial data line starting with "I"
                                    # If no categories were found either, this subsection is empty.
                                    if not actual_category_codes:
                                        logging.debug(f"Page {current_page_num}, Course {current_course_name}: No categories or initial data line found for this subsection with level '{current_level}'.")
                                        break # Break from while True for subsections

                            actual_rank_percentiles = rank_percentile_re.findall(data_values_text.strip())
                            logging.info(f"Page {current_page_num}, Course {current_course_name}, Level '{current_level}': Ranks/Percentiles: {actual_rank_percentiles} from text: '{data_values_text}'")

                            if not actual_category_codes and not actual_rank_percentiles:
                                # If this subsection yielded nothing, break from the subsection loop.
                                # This might happen if we consumed a level header but then found no valid categories/data.
                                logging.debug(f"Page {current_page_num}, Course {current_course_name}: Empty subsection after level '{current_level}'. Breaking subsection loop.")
                                break


                            for i, category_code in enumerate(actual_category_codes):
                                if i < len(actual_rank_percentiles):
                                    serial_number += 1
                                    rank, percentile = actual_rank_percentiles[i]
                                    row = [
                                        str(serial_number), str(current_page_num),
                                        current_college_code, current_college_name,
                                        current_course_code, current_course_name, current_status,
                                        current_level, "I", category_code, rank, percentile
                                    ]
                                    extracted_data_rows.append(row)
                                    logging.debug(f"Page {current_page_num}: Added row: {row}")
                                else:
                                    logging.warning(f"Page {current_page_num}, Course {current_course_name}, Level '{current_level}': Mismatched data: Cat: {category_code}, but not enough R/P pairs.")

                            # Check if the next line indicates a start of a new structure (college, course, or even a new level for a new subsection)
                            # or if it's the end of the page lines.
                            if line_idx >= len(lines) or \
                               college_re.match(lines[line_idx].strip()) or \
                               course_re.match(lines[line_idx].strip()):
                                break # Break from while True (subsections)

                            # If the next line is not a new Level header for a *new* subsection, break.
                            # This is tricky: how to know if the next line is a new level for the *same* course or start of something else?
                            # For now, if there are no more data lines starting with "I " immediately after current data, assume end of subsections for this course.
                            if not data_line_detect_re.match(lines[line_idx].strip()) and \
                               not any(level_re.search(lines[line_idx].strip()) for level_re in level_patterns):
                                break # Break from while True (subsections) if next line isn't data or a new level.


                        # After exiting the subsection loop for a course
                        if course_match: # This was the entry point for this course block
                            continue # To the main line processing loop (while line_idx < len(lines)) to find next college/course on the page

                    # If not a college, not a course (that we could process), and not a level header (handled at top of loop)
                    line_idx += 1
            # End of per-page processing loop

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
    # For iterative testing of Level detection, focus on a few key pages
    # output_csv_path_main = "debug_level_test_output.csv"
    # num_pages_to_process_main = 6 # Process up to page 6 to see variations

    # For full 17-page run:
    output_csv_path_main = "output_first_17_pages.csv"
    num_pages_to_process_main = 17


    if not os.path.exists(pdf_file_path_main):
        print(f"Test PDF file not found: {pdf_file_path_main}")
    else:
        extract_first_page_content(pdf_file_path_main, output_csv_path_main, max_pages_to_process=num_pages_to_process_main)
        print(f"Standalone run for {num_pages_to_process_main} pages. Output to {output_csv_path_main}. Check first_page_extraction.log for details.")
