import pdfplumber
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

pdf_path = "2024-Cutoff-Maharashtra.pdf"

try:
    with pdfplumber.open(pdf_path) as pdf:
        for i in range(min(3, len(pdf.pages))): # Process pages 0, 1, 2 (i.e., PDF pages 1, 2, 3)
            page_num_actual = i + 1
            page = pdf.pages[i]
            logging.info(f"--- Extracting tables from PDF Page {page_num_actual} ---")

            # Extract text first to find keywords if needed to locate tables, though extract_tables() is often robust.
            # text = page.extract_text()
            # logging.info(f"Raw text from page {page_num_actual}:\n{text[:500]}...") # Log first 500 chars

            tables = page.extract_tables() # Using default table extraction settings initially

            if tables:
                logging.info(f"Found {len(tables)} table(s) on page {page_num_actual}.")
                for idx, table_data in enumerate(tables):
                    logging.info(f"Table {idx+1} on page {page_num_actual} (first 5 rows):")
                    for row_idx, row in enumerate(table_data[:5]): # Log first 5 rows of each table
                        logging.info(f"  Row {row_idx}: {row}")
                    if len(table_data) > 5:
                        logging.info("  ... (more rows in this table)")

                    # Specifically look for "Instrumentation Engineering" related table on page 2
                    if page_num_actual == 2:
                        # Check if table content hints at "Instrumentation Engineering"
                        # This is a heuristic for logging purposes.
                        # A more robust way would be to correlate with prior regex findings in the main script.
                        flat_table_text = " ".join([" ".join(filter(None,r)) for r in table_data if r]) # Join all cell text
                        if "Instrumentation Engineering" in flat_table_text or "0100246610" in flat_table_text:
                             logging.info(f"!!! POTENTIAL 'Instrumentation Engineering' TABLE (Table {idx+1}) on Page 2 !!!")
                             logging.info(f"Full data for this potential table:")
                             for row_idx_full, row_full in enumerate(table_data):
                                 logging.info(f"  Full Row {row_idx_full}: {row_full}")


            else:
                logging.info(f"No tables found on page {page_num_actual} using default settings.")

            # Example of trying different table settings if default is not good (for future reference)
            # table_settings = {
            #     "vertical_strategy": "lines",
            #     "horizontal_strategy": "lines",
            # }
            # tables_with_settings = page.extract_tables(table_settings)
            # if tables_with_settings:
            #     logging.info(f"Found {len(tables_with_settings)} table(s) on page {page_num_actual} using custom settings.")
            # else:
            #     logging.info(f"No tables found on page {page_num_actual} using custom settings either.")

except Exception as e:
    logging.error(f"An error occurred: {e}", exc_info=True)

logging.info("--- PDFPlumber exploration finished ---")
