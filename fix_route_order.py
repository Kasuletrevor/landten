"""Fix the route order in payments.py - move /export before /{payment_id}"""

import re

# Read the file
with open("backend/app/routers/payments.py", "r") as f:
    content = f.read()

# Extract the export section (from the comment to the end of the function)
export_pattern = r"(\n# =+\n# Export Endpoints\n# =+\n\nfrom app\.services\.export_service import ExportService.*?)(?=\n# Export Endpoints|\Z)"
export_match = re.search(export_pattern, content, re.DOTALL)

if not export_match:
    print("Export section not found!")
    exit(1)

export_section = export_match.group(1)

# Remove the export section from the end
content_without_export = content[: export_match.start()] + content[export_match.end() :]

# Find the position after /overdue route (line ~489)
# Look for the pattern: result = [enrich_payment_with_tenant... followed by return PaymentListResponse... followed by \n\n@router.get
overdue_end_pattern = r"(result = \[enrich_payment_with_tenant\(p, session\) for p in payments\]\n    return PaymentListResponse\(payments=result, total=len\(result\)\)\n)(\n\n@router\.get)"

match = re.search(overdue_end_pattern, content_without_export)
if not match:
    print("Could not find insertion point!")
    exit(1)

# Insert the export section
insert_position = match.end(1)
new_content = (
    content_without_export[:insert_position]
    + export_section
    + content_without_export[insert_position:]
)

# Write the file back
with open("backend/app/routers/payments.py", "w") as f:
    f.write(new_content)

print("Route order fixed!")
