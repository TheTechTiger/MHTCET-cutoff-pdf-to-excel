import PyPDF2
import re
import logging

# Setup logging to a new file
logging.basicConfig(filename='first_page_extraction.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s', filemode='w')

def extract_first_page_content(pdf_path):
    """
    Extracts content line by line from the first page of a PDF using regex
    and logs each line.
    """
    logging.info(f"Starting extraction from PDF: {pdf_path}")
    try:
        with open(pdf_path, 'rb') as f_pdf:
            reader = PyPDF2.PdfReader(f_pdf)
            
            if not reader.pages:
                logging.warning("The PDF file has no pages.")
                print("The PDF file has no pages.")
                return

            # Get the first page
            first_page = reader.pages[0]
            page_text = first_page.extract_text()

            if not page_text:
                logging.warning("Could not extract any text from the first page.")
                print("Could not extract any text from the first page.")
                return

            # Split the extracted text into lines
            lines = page_text.split('\n')
            logging.info(f"--- Processing first page of {pdf_path} ---")
            print(f"Processing first page of {pdf_path}...")

            # Use a simple regex to capture the entire line
            line_regex = re.compile(r".*")

            for i, line in enumerate(lines):
                # Find all matches in the line (in this case, the whole line)
                match = line_regex.search(line)
                if match:
                    extracted_content = match.group(0)
                    # Log the extracted line content
                    logging.info(f"Line {i+1}: {extracted_content}")
            
            logging.info("--- Finished processing first page ---")
            print("Extraction from the first page is complete. Check 'first_page_extraction.log'.")

    except FileNotFoundError:
        error_msg = f"Error: The PDF file '{pdf_path}' was not found."
        logging.error(error_msg)
        print(error_msg)
    except Exception as e:
        error_msg = f"An unexpected error occurred: {e}"
        logging.error(error_msg, exc_info=True)
        print(error_msg)

if __name__ == "__main__":
    pdf_file_path = "2024-Cutoff-Maharashtra.pdf"
    extract_first_page_content(pdf_file_path)