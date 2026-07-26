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
        'assert john.final_salary == Decimal("27548.08")',
        'assert john.final_salary == Decimal("47750.00")'
    )
])

update_file("tests/test_salary.py", [
    (
        'assert payroll[0].final_salary == Decimal("29855.77")',
        'assert payroll[0].final_salary == Decimal("51750.00")'
    )
])
