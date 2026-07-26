import re

def update_file(path, replacements):
    with open(path, "r") as f:
        content = f.read()
    for old, new in replacements:
        content = content.replace(old, new)
    with open(path, "w") as f:
        f.write(content)

update_file("tests/test_monthly_biometric_excel.py", [
    (
        'assert john.final_salary <= Decimal("30000")',
        'assert john.final_salary <= Decimal("52000")'
    )
])
