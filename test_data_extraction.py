import unittest
import os
import filecmp
from data_extractor import extract_data_from_pdf # Import the renamed function

class TestPdfDataExtraction(unittest.TestCase):

    def setUp(self):
        self.pdf_path = "2024-Cutoff-Maharashtra.pdf"
        self.expected_output_path = "expected_17_page_output.csv"
        self.actual_output_path = "temp_actual_17_page_output.csv"
        # Ensure no previous actual output file exists
        if os.path.exists(self.actual_output_path):
            os.remove(self.actual_output_path)

    def test_extract_17_pages_content(self):
        # Ensure the PDF file exists
        self.assertTrue(os.path.exists(self.pdf_path), f"PDF file not found: {self.pdf_path}")
        # Ensure the expected output CSV file exists
        self.assertTrue(os.path.exists(self.expected_output_path), f"Expected output CSV file not found: {self.expected_output_path}")

        # Call the function to extract data from the PDF (first 17 pages)
        extract_data_from_pdf(self.pdf_path, self.actual_output_path, max_pages_to_process=17)

        # Check if the actual output file was created
        self.assertTrue(os.path.exists(self.actual_output_path), f"Actual output file was not created: {self.actual_output_path}")

        # Compare the actual content with the expected content byte-for-byte
        # filecmp.cmp is good for byte-by-byte.
        # For more detailed diffs in case of mismatch, could read and compare line by line.
        files_match = filecmp.cmp(self.actual_output_path, self.expected_output_path, shallow=False)

        if not files_match:
            # To provide more info on failure, read and compare contents
            with open(self.actual_output_path, 'rb') as f_actual, open(self.expected_output_path, 'rb') as f_expected:
                actual_content = f_actual.read()
                expected_content = f_expected.read()
            self.assertEqual(actual_content, expected_content,
                             "The extracted 17-page content does not match the expected output content.")

        self.assertTrue(files_match, "The extracted 17-page content does not match the expected output content (checked with filecmp).")


    def tearDown(self):
        # Clean up the temporary actual output file after the test
        if os.path.exists(self.actual_output_path):
            os.remove(self.actual_output_path)

if __name__ == '__main__':
    unittest.main()
