from pypdf import PdfReader
import re, json, os

# Changed this line to use the specific PDF file
reader = PdfReader("2024-Cutoff-Maharashtra.pdf")

alldata = {}

CurrentEntry = {
    "collegeName": "",
    "branches": {},
}

currents = {
    "college_name": "",
    "branch": "",
    "SeatLevel": "",
    "ress": [],
    "ressIndex": 0,
    "nextExpected": "",
}

skippedPages = []

for pageNO, page in enumerate(reader.pages):
    complete_page_text = page.extract_text()
    # if "II" in complete_page_text:
    #     skippedPages.append([pageNO, complete_page_text])
    #     continue
    complete_page_text = complete_page_text.split("\n")
    lineNo = 0
    skippedText = ""
    while lineNo < len(complete_page_text):
        line = complete_page_text[lineNo]
        lineNo += 1

        if "Legends: Starting" in line:
            break

        elif line in ['D', 'i'] or "Cut Off List for Maharashtra" in line or "State Common Entrance Tes" in line or "Degree Courses In Engineering and Technology" in line:
            continue

        elif line[:5]+" - " in line: # This seems to be a college code + name pattern
            currents["college_name"] = line
            if line not in alldata: alldata[line] = {}

        elif re.match(r'^\d{10}', line): # This seems to be a 10-digit course code
            if line not in alldata[currents["college_name"]]: alldata[currents["college_name"]][line] = {}
            currents["branch"] = line

            # The next line is expected to be status
            if lineNo < len(complete_page_text): # Check if there is a next line
                next_line_for_status = complete_page_text[lineNo]
                if "Status: " in next_line_for_status:
                    alldata[currents["college_name"]][currents["branch"]]["status"] = next_line_for_status.replace("Status: ", "")
                    lineNo += 1 # Consume status line
            else: # No more lines on the page after branch code
                pass


        elif "Home University" in line or "State Level" in line: # Seat Type
            currents["SeatLevel"] = line
            alldata[currents["college_name"]][currents["branch"]][currents["SeatLevel"]] = {}

            if lineNo >= len(complete_page_text): break # End of page before reservation categories
            next_line_for_ress = complete_page_text[lineNo]
            lineNo += 1

            currents["ress"] = next_line_for_ress.split(" ")
            # Sometimes reservation categories span multiple lines
            while lineNo < len(complete_page_text) and \
                  "  I " not in complete_page_text[lineNo] and \
                  "  II " not in complete_page_text[lineNo] and \
                  "Stage" not in complete_page_text[lineNo] and \
                  re.search(r'\(\d+\.?\d*\)', complete_page_text[lineNo]) is None: # Stop if we see a percentile line

                additional_ress_line = complete_page_text[lineNo]
                lineNo += 1
                currents["ress"] += additional_ress_line.split(" ")

            currents["ress"] = [r for r in currents["ress"] if r and r != '-'] # Filter out empty strings and placeholders

            if not currents["ress"]: # If no valid reservation categories found, skip this block
                skippedText += line + "\n(No reservation categories found)\n"
                continue

            for ress_item in currents["ress"]:
                alldata[currents["college_name"]][currents["branch"]][currents["SeatLevel"]][ress_item] = [-1.0,-1] # [Percentile, Rank]

            # Next line has the first rank or percentile data
            if lineNo >= len(complete_page_text): break # End of page

            current_data_line = complete_page_text[lineNo]

            # Check if the current line is rank data (I or II) or percentile data
            is_rank_line = "  I " in current_data_line or "  II " in current_data_line
            is_percentile_line = re.search(r'\(\d+\.?\d*\)', current_data_line) is not None

            if is_rank_line:
                line_text_for_rank = current_data_line.replace("  I ", '').replace("  II ", '').strip()
                lineNo += 1
                try:
                    rank = int(line_text_for_rank)
                except ValueError:
                    rank = -1
                if currents["ress"]: # Check if ress is not empty
                    alldata[currents["college_name"]][currents["branch"]][currents["SeatLevel"]][currents["ress"][currents["ressIndex"]]][1] = rank

            # Process lines with percentiles and subsequent ranks
            while lineNo < len(complete_page_text):
                if currents["ressIndex"] >= len(currents["ress"]): # Safety break
                    currents["ressIndex"] = 0
                    break

                current_data_line = complete_page_text[lineNo]

                percentile_match = re.search(r'\((\d+\.?\d*)\)', current_data_line)
                if percentile_match:
                    perTile = float(percentile_match.group(1))
                    alldata[currents["college_name"]][currents["branch"]][currents["SeatLevel"]][currents["ress"][currents["ressIndex"]]][0] = perTile

                    NextRankText = current_data_line[current_data_line.rfind(')')+1:].strip()
                    currents["ressIndex"] += 1

                    if NextRankText == 'Stage' or NextRankText == '' or NextRankText == '-':
                        if currents["ressIndex"] < len(currents["ress"]): # More reservation categories but no rank for current one
                             # Check if next line is a rank for the next category
                            if lineNo + 1 < len(complete_page_text):
                                next_processing_line = complete_page_text[lineNo+1]
                                if "  I " in next_processing_line or "  II " in next_processing_line : # It's a rank for next category
                                    currents["ressIndex"] = 0 # Reset for the main rank line processing
                                    break
                        else: # No more categories
                            currents["ressIndex"] = 0
                            break
                    elif currents["ressIndex"] < len(currents["ress"]): # If there are more reservation categories
                        try:
                            next_rank_val = int(NextRankText)
                            alldata[currents["college_name"]][currents["branch"]][currents["SeatLevel"]][currents["ress"][currents["ressIndex"]]][1] = next_rank_val
                        except ValueError:
                             # Not a rank for the next category, assume it's end of this block or needs new logic
                            currents["ressIndex"] = 0 # Reset and break
                            break
                    else: # No more reservation categories, but found text after percentile.
                        currents["ressIndex"] = 0
                        break
                else: # Line does not contain percentile, might be a new rank line or end of block
                    currents["ressIndex"] = 0 # Reset for next seat level block
                    break
                lineNo += 1
            currents["ressIndex"] = 0 # Ensure reset after processing a block

        else:
            skippedText += line+"\n"

    extracted_text_for_check = page.extract_text().replace("\n", '')
    processed_text_len = sum(len(s.replace("\n", "")) for s in complete_page_text) - len(skippedText.replace("\n", ""))

    if not extracted_text_for_check.strip(): # Empty page
        print(f"Page {pageNO+1} is empty or unreadable.")
    elif not skippedText.strip() and processed_text_len > 0: # Nothing skipped, something processed
        print(f"Page {pageNO+1} Processed successfully.")
    elif skippedText.replace("\n",'') == extracted_text_for_check :
        skippedPages.append([pageNO, page.extract_text()])
        print(f"Page {pageNO+1} Skipped (Full content in skippedText)")
    elif skippedText.strip():
        skippedPages.append([pageNO, skippedText])
        print(f"Page {pageNO+1} partially processed (Review skipped text for page {pageNO+1})")
    else: # Default case, should ideally not be hit if logic above is complete
        print(f"Page {pageNO+1} processing status unclear.")


with open("data.json", "w") as outfile:
    outfile.write(json.dumps(alldata, indent=4))

# os.makedirs("skipped", exist_ok=True) # Temporarily disable creating skipped files
# for pageNo_idx, page_content_text in skippedPages:
#     with open(f"skipped/{pageNo_idx+1}.txt", "w", encoding='utf-8') as outfile: # Added encoding
#         outfile.write(page_content_text)

print("Processing complete. Check data.json. Skipped file generation is currently disabled.")
