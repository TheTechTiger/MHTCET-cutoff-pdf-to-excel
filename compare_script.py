import csv

def parse_csv_content(csv_content_string):
    lines = csv_content_string.strip().splitlines()
    reader = csv.reader(lines)
    return [row for row in reader if row]

# Read file contents
with open("standalone_17_page_run_output.csv", 'r', encoding='utf-8') as f:
    actual_csv_content = f.read()
with open("expected_17_page_output.csv", 'r', encoding='utf-8') as f:
    expected_csv_content = f.read()

actual_data = parse_csv_content(actual_csv_content)
expected_data = parse_csv_content(expected_csv_content)

differences = []
num_actual_rows = len(actual_data)
num_expected_rows = len(expected_data)

if num_actual_rows != num_expected_rows:
    differences.append({
        "type": "row_count_mismatch",
        "actual_rows": num_actual_rows,
        "expected_rows": num_expected_rows
    })

if num_actual_rows > 0 and num_expected_rows > 0:
    if actual_data[0] != expected_data[0]:
        differences.append({
            "type": "header_mismatch",
            "actual_header": actual_data[0],
            "expected_header": expected_data[0]
        })

common_total_rows = min(num_actual_rows, num_expected_rows)
start_row_index = 1

for i in range(start_row_index, common_total_rows):
    row_actual = actual_data[i]
    row_expected = expected_data[i]

    max_fields = max(len(row_actual), len(row_expected))
    row_actual_normalized = row_actual + [''] * (max_fields - len(row_actual))
    row_expected_normalized = row_expected + [''] * (max_fields - len(row_expected))

    if row_actual_normalized != row_expected_normalized:
        field_diffs = []
        for j in range(max_fields):
            actual_field_val = row_actual[j] if j < len(row_actual) else ""
            expected_field_val = row_expected[j] if j < len(row_expected) else ""

            if actual_field_val != expected_field_val:
                field_diffs.append({
                    "field_index": j,
                    "header": expected_data[0][j] if j < len(expected_data[0]) else "N/A",
                    "actual_field": actual_field_val,
                    "expected_field": expected_field_val
                })
        if field_diffs:
            differences.append({
                "type": "row_mismatch",
                "line_number": i + 1,
                "field_differences": field_diffs,
            })

if num_actual_rows > num_expected_rows:
    for i in range(num_expected_rows, num_actual_rows):
        differences.append({
            "type": "extra_actual_row",
            "line_number": i + 1,
            "actual_row": actual_data[i]
        })
elif num_expected_rows > num_actual_rows:
    for i in range(num_actual_rows, num_expected_rows):
        differences.append({
            "type": "extra_expected_row",
            "line_number": i + 1,
            "expected_row": expected_data[i]
        })

if not differences:
    comparison_message = "SUCCESS: The generated output matches the expected output perfectly."
else:
    comparison_message = f"Found differences between generated and expected output.\n"

    row_count_mismatch = next((d for d in differences if d["type"] == "row_count_mismatch"), None)
    if row_count_mismatch:
        comparison_message += f"- Row count mismatch: Actual={row_count_mismatch['actual_rows']} (incl header), Expected={row_count_mismatch['expected_rows']} (incl header)\n"

    header_mismatch = next((d for d in differences if d["type"] == "header_mismatch"), None)
    if header_mismatch:
        comparison_message += f"- Header mismatch. Actual: {header_mismatch['actual_header']}, Expected: {header_mismatch['expected_header']}\n"

    row_mismatches = [d for d in differences if d["type"] == "row_mismatch"]
    if row_mismatches:
        comparison_message += f"- Found {len(row_mismatches)} mismatched data rows. First few mismatches:\n"
        for i, diff in enumerate(row_mismatches[:5]):
            comparison_message += f"  - Line {diff['line_number']} (1-based CSV line):\n"
            for fd in diff['field_differences'][:3]:
                comparison_message += f"    - Field '{fd['header']}' (idx {fd['field_index']}): Actual='{fd['actual_field']}', Expected='{fd['expected_field']}'\n"
            if len(diff['field_differences']) > 3:
                comparison_message += "    - ... (more fields differ in this row)\n"

    extra_actual_rows = [d for d in differences if d["type"] == "extra_actual_row"]
    if extra_actual_rows:
        comparison_message += f"- Found {len(extra_actual_rows)} extra row(s) in actual output. First few at lines (1-based CSV line): {[d['line_number'] for d in extra_actual_rows[:3]]}\n"

    extra_expected_rows = [d for d in differences if d["type"] == "extra_expected_row"]
    if extra_expected_rows:
        comparison_message += f"- Found {len(extra_expected_rows)} extra row(s) in expected output (missing from actual). First few at lines (1-based CSV line): {[d['line_number'] for d in extra_expected_rows[:3]]}\n"

MAX_MESSAGE_LENGTH = 4000
if len(comparison_message) > MAX_MESSAGE_LENGTH:
    comparison_message = comparison_message[:MAX_MESSAGE_LENGTH - 35] + "\n... (message truncated due to length)"

print(comparison_message)
