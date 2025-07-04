import PyPDF2 # For reading PDF and extracting text
import pandas as pd
import re

# This function might still be useful for parsing specific lines
def extract_college_course_from_text(text):
    """
    Extracts college name, code and course name, code from a string.
    Assumes the string might contain college code, name and then course code, name.
    Example: "3001 - Government College of Engineering, Amravati 300124510 - Computer Science and Engineering"
    """
    college_name = "Unknown College"
    course_name = "Unknown Course"

    # Try to find college code and name (e.g., "3001 - Government College of Engineering, Amravati")
    college_match = re.search(r"(\d{4})\s*-\s*([^0-9]+?)(?=\s*\d{10}|$)", text)
    if college_match:
        college_code = college_match.group(1).strip()
        college_name = f"{college_code} - {college_match.group(2).strip()}"

        # Try to find course code and name within the remaining part or the original text
        # (e.g., "300124510 - Computer Science and Engineering")
        course_text_search_area = text[college_match.end():] if college_match.end() < len(text) else text
        course_match = re.search(r"(\d{10})\s*-\s*(.+)", course_text_search_area)
        if course_match:
            course_code = course_match.group(1).strip()
            course_name = f"{course_code} - {course_match.group(2).strip()}"
        else: # Fallback if course not found after college
            course_match_simple = re.search(r"(\d{10})\s*-\s*(.+)", text)
            if course_match_simple:
                 course_name = f"{course_match_simple.group(1).strip()} - {course_match_simple.group(2).strip()}"


    else: # Fallback if college pattern "XXXX - Name" is not found
        # Simpler extraction if the combined pattern fails
        # Look for a course code and name first
        course_match_simple = re.search(r"(\d{10})\s*-\s*(.+)", text)
        if course_match_simple:
            course_name = f"{course_match_simple.group(1).strip()} - {course_match_simple.group(2).strip()}"
            # Try to get college name from text before course
            possible_college_text = text[:course_match_simple.start()].strip()
            if possible_college_text:
                college_name = possible_college_text


    return college_name, course_name

# The process_table function is removed as it's not suitable for line-by-line text parsing.
# New parsing logic will be integrated into the main() function or new helper functions.

def main(pdf_path):
    all_records = []
    current_college_name = ""
    current_course_name = ""
    current_status = ""
    current_seat_type = ""
    # TODO: Add more state variables as needed for multi-line parsing

    try:
        with open(pdf_path, 'rb') as f_pdf:
            reader = PyPDF2.PdfReader(f_pdf)
            total_pages = len(reader.pages)
            print(f"PDF has {total_pages} pages.")

            print(f"Processing all {total_pages} pages.")

            for page_idx in range(total_pages): # Iterate through all pages
                page_num_actual = page_idx + 1 # 1-indexed for user display
                # if not (start_page_debug <= page_num_actual <= end_page_debug): # Removed page limit
                #     continue

                page = reader.pages[page_idx]
                page_text = page.extract_text()
                if not page_text:
                    print(f"Page {page_num_actual} has no extractable text. Skipping.")
                    continue

                print(f"\nProcessing Page {page_num_actual}/{total_pages}...")
                lines = page_text.split('\n')

                line_idx = 0

                # State variables for parsing data blocks
                active_categories = []
                expecting_percentiles = False
                expecting_ranks = False
                current_stage = "N/A" # Default, can be updated if Stage I/II found

                while line_idx < len(lines):
                    line = lines[line_idx].strip()
                    line_idx += 1

                    if not line: # Skip empty lines
                        continue

                    # --- Common page elements to skip ---
                    if "Cut Off List for Maharashtra State" in line or \
                       "State Common Entrance Test Cell" in line or \
                       "Maharashtra State, Mumbai" in line or \
                       "Published on" in line or \
                       re.match(r"Page No\.", line) or \
                       "Legends:" in line: # Stop processing if legends section is reached on page
                        # if "Legends:" in line : current_college_name = "" # Removed reset for now
                        continue

                    # Try to extract college name using the existing helper
                    # This regex looks for "XXXX - College Name"
                    college_match_re = r"^(\d{4})\s*-\s*(.+)"
                    college_m = re.match(college_match_re, line)
                    if college_m:
                        current_college_name = line # Use the full line as it appears
                        current_course_name = "" # Reset course when new college is found
                        current_status = ""
                        current_seat_type = ""
                        active_categories = []
                        # print(f"  College: {current_college_name}") # SILENCED
                        continue

                    # Try to extract course name
                    # This regex looks for "XXXXXXXXXX - Course Name"
                    course_match_re = r"^(\d{10})\s*-\s*(.+)"
                    course_m = re.match(course_match_re, line)
                    if course_m:
                        current_course_name = line # Use the full line
                        # Check for status on the *same* line (sometimes happens)
                        if "Status:" in current_course_name:
                            current_status = current_course_name.split("Status:")[-1].strip()
                            current_course_name = current_course_name.split("Status:")[0].strip()
                        else: # Reset status if not on the same line
                            current_status = "" # Status might be on next line
                        current_seat_type = ""
                        active_categories = []
                        # print(f"    Course: {current_course_name}") # SILENCED
                        # Check next line for status if not found on course line
                        if not current_status and line_idx < len(lines):
                            next_line_check = lines[line_idx].strip()
                            if next_line_check.startswith("Status:"):
                                current_status = next_line_check.replace("Status:", "").strip()
                                # print(f"      Status: {current_status}") # SILENCED
                                line_idx +=1 # Consume status line
                        continue

                    # Explicit status line check if not caught by course line logic
                    if line.startswith("Status:"):
                        current_status = line.replace("Status:", "").strip()
                        # print(f"      Status: {current_status}") # SILENCED
                        continue

                    # Seat Type Headers (e.g., Home University, State Level)
                    # These often precede the category headers.
                    if "Home University" in line or "State Level" in line or "All India" in line or \
                       "Minority Seats" in line or "Other Than Home University" in line:
                        # More specific checks might be needed if these keywords appear elsewhere
                        # For now, assume if they are on a line by themselves or with "Seats", it's a seat type
                        if len(line.split()) < 10: # Heuristic: seat type lines are usually short
                            current_seat_type = line
                            active_categories = [] # Reset categories for new seat type
                            # print(f"        Seat Type: {current_seat_type}") # SILENCED
                            # The next line is often the category headers
                            if line_idx < len(lines):
                                next_line_for_cats = lines[line_idx].strip()
                                # Check if next line looks like categories (multiple uppercase words)
                                possible_cats = [word for word in next_line_for_cats.split() if re.fullmatch(r'[A-Z]+[HS]?', word)]
                                if len(possible_cats) > 2: # Heuristic for a category line
                                    active_categories = possible_cats
                                    # print(f"          Categories: {active_categories}") # SILENCED
                                    line_idx += 1 # Consumed category line
                                    # The line after categories could be percentiles or ranks
                                    # This part of state (expecting_percentiles/ranks) needs to be refined
                                # The line after categories could be percentiles or ranks - state will be set by Stage lines or by finding categories themselves
                            continue # Processed seat type

                    # Category header line detection (independent of seat type, but seat type should be known)
                    # A line with multiple short, uppercase words, not matching other patterns.
                    # Example: GOPENH LOPENH GSCH LSCH GSTH LSTH GNT1H LNT1H GNT2H LNT2H GNT3H LNT3H GOBC HLOBC HSCHH LSCOH ...
                    # Ensure it's not a college/course line or status line by checking its start.
                    if not re.match(r"^\d{4}\s*-", line) and not re.match(r"^\d{10}\s*-", line) and not line.startswith("Status:"):
                        possible_cats_on_line = [word for word in line.split() if re.fullmatch(r'[A-Z]+[HS]?', word) and len(word) > 1]
                        # Heuristic: if a line has many such words, it's likely a category header.
                        # And it shouldn't contain numbers with decimals (percentiles)
                        if len(possible_cats_on_line) > 3 and not re.search(r'\d\.\d', line): # More than 3 categories, no scores
                            active_categories = possible_cats_on_line
                            # print(f"          Categories (direct detect): {active_categories}") # SILENCED
                            # When categories are found, assume Stage-I (percentiles) unless Stage-II was just active
                            if current_stage != "Stage-II": # If it was Stage-II, we might need ranks for *previous* cats, this logic is tricky
                                current_stage = "Stage-I" # Default to Stage-I when new cats found
                                expecting_percentiles = True
                                expecting_ranks = False
                            # If current_stage *was* Stage-II, finding new categories implies the old block is done.
                            # So, setting to Stage-I for these new categories is reasonable.
                            else: # current_stage was "Stage-II"
                                current_stage = "Stage-I"
                                expecting_percentiles = True
                                expecting_ranks = False

                            # Reset expecting_ranks if we just found new categories and set to Stage-I
                            # This ensures that if Stage-II was previously set, it doesn't bleed over if a new cat line appears.
                            # This state reset is important.
                            # print(f"            Set to expect percentiles for these new categories, Stage: {current_stage}") # SILENCED
                            continue


                    # Stage lines (Stage-I, Stage-II)
                    if line.startswith("Stage-I"):
                        current_stage = "Stage-I"
                        expecting_percentiles = True # Stage I is usually percentile
                        expecting_ranks = False
                        # print(f"          Stage: {current_stage}") # SILENCED
                        continue
                    elif line.startswith("Stage-II"):
                        current_stage = "Stage-II"
                        expecting_ranks = True # Stage II is usually rank
                        expecting_percentiles = False
                        # print(f"          Stage: {current_stage}") # SILENCED
                        continue

                    # Data line processing (scores) - This is the most complex part
                    # This assumes `active_categories` is already populated.
                    if active_categories and (expecting_percentiles or expecting_ranks):
                        # Try to parse scores from the line. Scores can be percentiles (90.123) or ranks (12345).
                        # They might be plain or in parentheses.
                        # A line of scores should roughly correspond to the number of active_categories.

                        # New regex to better capture combined (percentile)rank forms as single tokens
                        # Order matters: try to match combined forms first.
                        score_finder_re = r"(\(\s*\d+\.\d+\s*\)\s*\d+|\d+\.\d+\s*\(\s*\d+\s*\)|\(\s*\d+\.\d+\s*\)|\d+\.\d+|\d+|-)"
                        score_values_from_line = re.findall(score_finder_re, line)

                        cleaned_scores = []
                        for s_val in score_values_from_line:
                            # s_val here is already a string from findall's capture group
                            s_clean = s_val.strip() # General strip
                            if s_clean == '-':
                                cleaned_scores.append("N/A")
                            elif s_clean: # Ensure not empty after strip
                                cleaned_scores.append(s_clean)

                        # print(f"DEBUG: Line: '{line}' -> Raw scores from regex: {score_values_from_line} -> Cleaned scores: {cleaned_scores}")


                        if len(cleaned_scores) > 0 and len(cleaned_scores) <= len(active_categories) + 2 and len(cleaned_scores) >= len(active_categories) -2 : # Heuristic: number of scores is close to num categories
                            # print(f"            Data for {current_stage}?: {line} -> Scores: {cleaned_scores}") # SILENCED
                            for i, category in enumerate(active_categories):
                                if i < len(cleaned_scores):
                                    score_val = cleaned_scores[i]
                                    percentile = "N/A"
                                    rank = "N/A"
                                    original_score_val_for_debug = score_val # For debug print

                                    # Try to parse combined (percentile)rank or percentile(rank)
                                    # Example: (98.12345)1234 or 98.12345(1234)
                                    # Regex: optional opening paren, digits.digits, optional closing paren, digits
                                    # Or, digits.digits, opening paren, digits, closing paren
                                    combined_match = re.match(r"\((\d+\.\d+)\)(\d+)", score_val) or \
                                                     re.match(r"(\d+\.\d+)\((\d+)\)", score_val)

                                    if combined_match:
                                        percentile = combined_match.group(1)
                                        rank = combined_match.group(2)
                                    elif score_val != "N/A": # Not combined and not already N/A
                                        is_percentile_format = bool(re.search(r"\d+\.\d+", score_val))
                                        is_integer_format = bool(re.fullmatch(r"\d+", score_val))

                                        if expecting_percentiles:
                                            if is_percentile_format:
                                                # Strip parens if it's like (xx.xx)
                                                percentile = score_val.strip("()") if score_val.startswith("(") and score_val.endswith(")") else score_val
                                            elif is_integer_format: # Rank appearing on a percentile line
                                                rank = score_val
                                            else: # Fallback if format is unexpected
                                                percentile = score_val.strip("()") if score_val.startswith("(") and score_val.endswith(")") else score_val
                                        elif expecting_ranks:
                                            if is_integer_format:
                                                rank = score_val
                                            elif is_percentile_format: # Percentile appearing on a rank line
                                                percentile = score_val.strip("()") if score_val.startswith("(") and score_val.endswith(")") else score_val
                                            else: # Fallback
                                                rank = score_val
                                        else: # Neither specifically expected, try to infer
                                            if is_percentile_format:
                                                percentile = score_val.strip("()") if score_val.startswith("(") and score_val.endswith(")") else score_val
                                            elif is_integer_format:
                                                rank = score_val
                                            # else: # Can't determine, leave as N/A

                                    if percentile != "N/A" or rank != "N/A":
                                        record = {
                                            "College Name": current_college_name,
                                            "Course Name": current_course_name,
                                            "Status": current_status,
                                            "Seat Type": current_seat_type,
                                            "Category": category,
                                            "Percentile": percentile,
                                            "Rank": rank,
                                            "Stage": current_stage
                                        }
                                        # print(f"DEBUG: Appending record: {record}") # SILENCED DEBUG LINE
                                        all_records.append(record)
                                    # else: # DEBUG LINE # SILENCED
                                        # print(f"DEBUG: Record NOT added. Category: {category}, P: {percentile}, R: {rank}, Stage: {current_stage}") # SILENCED DEBUG LINE
                                # else: # Not enough scores for all categories, stop for this line # SILENCED
                                    # print(f"DEBUG: Not enough scores ({len(cleaned_scores)}) for category '{category}' (index {i}) in active_categories ({len(active_categories)}). Line: {line}") # SILENCED DEBUG LINE
                                    # break # Breaking here might be too aggressive if some scores are valid.

                            # After processing a score line, what do we expect next?
                            # This depends on the PDF structure. Often, if Stage-I (percentiles) was processed,
                            # Stage-II (ranks) might follow for the SAME categories.
                            # Or, a new set of categories or a new course/college.
                            if expecting_percentiles:
                                # We might expect ranks next for the same categories, or a new Stage-II line
                                # For now, let's assume if it was Stage-I, the next data line could be ranks for same cats
                                # This requires more sophisticated state (e.g. remembering last categories and if they need ranks)
                                pass # current_stage and active_categories remain
                            elif expecting_ranks:
                                # After ranks, usually reset for new seat type or course
                                # active_categories = [] # Resetting here might be too soon
                                # current_stage = "N/A"
                                pass

                            # If this line was Stage-I, the next non-empty line could be Stage-II
                            # or directly the ranks. If it was Stage-II, then reset.
                            if current_stage == "Stage-I":
                                # Peek at next line for Stage-II or rank data
                                if line_idx < len(lines):
                                    peek_next_line = lines[line_idx].strip()
                                    if peek_next_line.startswith("Stage-II"):
                                        # Handled by Stage-II block at start of loop
                                        pass
                                    else: # Assume it might be ranks for current Stage-I categories
                                        # This means the next iteration of this data block should be `expecting_ranks = True`
                                        # This state transition is tricky.
                                        pass # Let the loop re-evaluate next line.
                            elif current_stage == "Stage-II":
                                active_categories = [] # Processed ranks for this block
                                current_stage = "N/A" # Reset stage

                            continue # Move to next line after processing a data line
                        # else:
                            # Line after categories didn't look like a matching score line
                            # active_categories = [] # Potentially reset if data not found as expected
                            # current_stage = "N/A"

                    # If line is not identifiable, it might be a continuation or unhandled data.
                    # For now, we just print it if it's not an empty line and some context is set.
                    # elif line and (current_college_name or current_course_name):
                        # print(f"      Unhandled line: {line}")


                # End of page processing (while loop for lines)
            # End of all pages processing (for loop for pages)

    except FileNotFoundError:
        print(f"Error: The PDF file '{pdf_path}' was not found.")
        return # Exit if PDF not found
    except PyPDF2.errors.PdfReadError:
        print(f"Error: Could not read or decrypt the PDF file '{pdf_path}'. It may be corrupted or password-protected.")
        return
    except Exception as e:
        print(f"An error occurred during PDF processing: {e}")
                # End of page processing
            # End of all pages processing

    except Exception as e:
        print(f"An error occurred during PDF processing: {e}")
        import traceback
        traceback.print_exc() # Print full traceback for debugging

    if not all_records:
        print("No records were extracted. The Excel file will not be created.")
        return

    final_df = pd.DataFrame(all_records)

    # Add Sr No.
    final_df.insert(0, 'Sr No.', range(1, len(final_df) + 1))

    # Clean up data:
    # Remove rows where Category might be "Category" (header misinterpretation)
    final_df = final_df[~final_df['Category'].isin(['Category', 'Seat Type', 'Stage'])]
    # Remove rows where essential data like College Name or Course Name is still default/unknown
    final_df = final_df[~final_df['College Name'].str.contains("Unknown College", case=False, na=False)] # Added na=False
    final_df = final_df[~final_df['Course Name'].str.contains("Unknown Course", case=False, na=False)] # Added na=False
    # Remove rows where both percentile and rank are N/A
    final_df = final_df[~((final_df['Percentile'] == "N/A") & (final_df['Rank'] == "N/A"))]


    if final_df.empty:
        print("No valid data after cleaning. CSV file will not be created.") # Updated message
        return

    try:
        csv_path = "list_without_college.csv"  # Changed to CSV path
        final_df.to_csv(csv_path, index=False) # Changed to to_csv
        print(f"Successfully created CSV file: {csv_path}") # Updated message
    except Exception as e:
        print(f"Error writing to CSV: {e}") # Updated message

if __name__ == "__main__":
    pdf_file = "2024-Cutoff-Maharashtra.pdf" # Make sure this file is in the same directory
    main(pdf_file)
