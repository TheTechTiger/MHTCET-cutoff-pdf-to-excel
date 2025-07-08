import PyPDF2
import re
import logging
import csv
import os

logging.basicConfig(filename='first_page_extraction.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s', filemode='w')

def extract_first_page_content(pdf_path, output_csv_path):
    logging.info(f"Starting regex-based extraction from PDF: {pdf_path}")
    logging.info(f"Output will be written to: {output_csv_path}")

    extracted_data_rows = []
    serial_number = 0
    header = ["Sr. No.","College Code","College Name","Course Code","Course Name","Status","Level","Stage","Caste_Category","Cutoff Rank","Cutoff Percentile"]

    try:
        with open(pdf_path, 'rb') as f_pdf:
            reader = PyPDF2.PdfReader(f_pdf)
            if not reader.pages:
                logging.warning("The PDF file has no pages.")
                with open(output_csv_path, 'w', newline='', encoding='utf-8') as csv_file:
                    csv_writer = csv.writer(csv_file)
                    csv_writer.writerow(header)
                return

            page_text = reader.pages[0].extract_text()
            if not page_text:
                logging.warning("Could not extract any text from the first page.")
                with open(output_csv_path, 'w', newline='', encoding='utf-8') as csv_file:
                    csv_writer = csv.writer(csv_file)
                    csv_writer.writerow(header)
                return

        lines = page_text.split('\n')

        current_college_code = ""
        current_college_name = ""
        current_level = "State Level"

        college_re = re.compile(r"(\d{5})\s*-\s*(.+)")
        course_re = re.compile(r"(\d{10})\s*-\s*(.+)")
        status_re = re.compile(r"Status:\s*(.+)")

        rank_percentile_re = re.compile(r"(\d+)\s*\(([\d.]+)\)")
        # data_line_prefix_re = re.compile(r"^\s*I\s+") # Detects "I   " - and consumes it
        # Modified to not consume, just detect, group the rest
        data_line_detect_re = re.compile(r"^\s*I\s+(.*)")


        skip_these_exact_lines = [
            "D", "i", "rState Common Entrance Test Cell",
            "Cut Off List for Maharashtra & Minority Seats of CAP Round I  for Admission to First Year of Four Year",
            "Degree Courses In Engineering and Technology & Master of Engineering and Technology (Integrated 5 Years ) for the Year 2024-25Government of Maharashtra",
            "State Level",
            "Stage",
            "Legends: Starting character G-General, L-Ladies, End character H-Home University, O-Other than Home University,S-State Level, AI- All India Seat.",
            "Maharashtra State Seats - Cut Off Indicates Maharashtra State General Merit No.; Figures in bracket Indicates Merit Percentile."
        ]

        line_idx = 0
        while line_idx < len(lines):
            line = lines[line_idx].strip()

            if not line or line in skip_these_exact_lines:
                line_idx += 1
                continue
            
            college_match = college_re.match(line)
            if college_match:
                current_college_code = college_match.group(1)
                college_name_str = college_match.group(2).strip().replace('\n', ' ').replace('\r', ' ')
                current_college_name = " ".join(college_name_str.split())
                logging.info(f"Matched College: {current_college_code} - {current_college_name}")
                line_idx += 1
                continue

            course_match = course_re.match(line)
            if course_match and current_college_code:
                current_course_code = course_match.group(1)
                course_name_str = course_match.group(2).strip().replace('\n', ' ').replace('\r', ' ')
                current_course_name = " ".join(course_name_str.split())
                logging.info(f"Matched Course: {current_course_code} - {current_course_name}")

                line_idx += 1
                current_status = ""
                if line_idx < len(lines):
                    status_line = lines[line_idx].strip()
                    status_match = status_re.match(status_line)
                    if status_match:
                        status_str = status_match.group(1).strip().replace('\n', ' ').replace('\r', ' ')
                        current_status = " ".join(status_str.split())
                        logging.info(f"Matched Status: {current_status}")
                        line_idx += 1
                    else:
                        logging.warning(f"Expected status line, found: {status_line} for course {current_course_name}")

                if line_idx < len(lines) and lines[line_idx].strip() == "State Level": # Explicitly skip if found
                    line_idx += 1

                category_codes_text = ""
                # Logic to collect category lines:
                # They are typically non-empty, not starting with "I ", not a college/course code, not "Status:", not "Stage", not "Legends"
                while line_idx < len(lines):
                    potential_cat_line = lines[line_idx].strip()
                    if not potential_cat_line or \
                       data_line_detect_re.match(potential_cat_line) or \
                       college_re.match(potential_cat_line) or \
                       course_re.match(potential_cat_line) or \
                       status_re.match(potential_cat_line) or \
                       potential_cat_line == "Stage" or \
                       "Legends:" in potential_cat_line:
                        break # Stop accumulating categories
                    category_codes_text += " " + potential_cat_line
                    line_idx += 1

                actual_category_codes = [code for code in category_codes_text.strip().split(' ') if code.isupper() and len(code)>1 and code != 'I']
                logging.info(f"Potential Categories: {actual_category_codes} for course {current_course_name}")

                data_values_text = ""
                # Logic to collect data lines:
                # First, try to match the initial line that MUST start with "I"
                if line_idx < len(lines): # Ensure there's a line to check
                    initial_data_match = data_line_detect_re.match(lines[line_idx].strip())
                    if initial_data_match:
                        data_values_text += " " + initial_data_match.group(1).strip()
                        line_idx += 1
                        # Now, continue collecting subsequent lines if they look like data continuation
                        while line_idx < len(lines):
                            potential_data_continuation_line = lines[line_idx].strip()
                            # Heuristic: if the line contains digits and common data characters, and is not a header
                            if potential_data_continuation_line and \
                               re.search(r'[\d\.\(\)]', potential_data_continuation_line) and \
                               not college_re.match(potential_data_continuation_line) and \
                               not course_re.match(potential_data_continuation_line) and \
                               not status_re.match(potential_data_continuation_line) and \
                               potential_data_continuation_line != "Stage" and \
                               "Legends:" not in potential_data_continuation_line:
                                data_values_text += " " + potential_data_continuation_line
                                line_idx += 1
                            else:
                                break # Line doesn't look like data continuation
                    else:
                        logging.debug(f"No initial data line starting with 'I' found for course {current_course_name} at line: {lines[line_idx].strip() if line_idx < len(lines) else 'EOF'}")

                actual_rank_percentiles = rank_percentile_re.findall(data_values_text.strip())
                logging.info(f"Potential Ranks/Percentiles: {actual_rank_percentiles} for course {current_course_name} from text: '{data_values_text}'")

                for i, category_code in enumerate(actual_category_codes):
                    if i < len(actual_rank_percentiles):
                        serial_number += 1
                        rank, percentile = actual_rank_percentiles[i]
                        row = [
                            str(serial_number), current_college_code, current_college_name,
                            current_course_code, current_course_name, current_status,
                            current_level, "I", category_code, rank, percentile
                        ]
                        extracted_data_rows.append(row)
                        logging.debug(f"Added row: {row}")
                    else:
                        logging.warning(f"Mismatched data for {current_course_name}: Cat: {category_code} at index {i}, but only {len(actual_rank_percentiles)} R/P pairs.")

                # After processing a course (whether data was found or not),
                # line_idx is now at the start of the next section or non-data line.
                # The main while loop will continue from here.
                # No 'continue' here, let it fall through to the main loop's line_idx increment if no other condition matches below.
                # This was a source of bugs. The 'continue' for course_match should be at the end of its block.
                if course_match: # If we entered this block due to a course match
                    continue # Restart the outer while loop to check the new line_idx

            # If no specific block matched (e.g. line was blank after strip, or some other text)
            line_idx += 1

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
    test_pdf_file_path = "2024-Cutoff-Maharashtra.pdf"
    # Outputting to the new standard expected file name for this plan step.
    standard_output_csv_file_path = "standard_expected_first_page_output.csv"

    if not os.path.exists(test_pdf_file_path):
        print(f"Test PDF file not found: {test_pdf_file_path}")
    else:
        extract_first_page_content(test_pdf_file_path, standard_output_csv_file_path)
        print(f"Standalone run. Output to {standard_output_csv_file_path}. Check first_page_extraction.log for details.")
