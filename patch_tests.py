import re

def update_file(path, replacements):
    with open(path, "r") as f:
        content = f.read()
    for old, new in replacements:
        content = content.replace(old, new)
    with open(path, "w") as f:
        f.write(content)

# 1. test_salary.py
update_file("tests/test_salary.py", [
    (
        'assert row.final_salary == Decimal("30000.00")',
        'assert row.final_salary == Decimal("52000.00")'
    ),
    (
        '# hourly from 30000 not 52000: 144.23 * 1h\n    assert payroll[0].salary_deduction == Decimal("144.23")',
        '# hourly from 52000: 52000/26/8 = 250\n    assert payroll[0].salary_deduction == Decimal("250.00")'
    )
])

# 2. test_monthly_biometric_excel.py
update_file("tests/test_monthly_biometric_excel.py", [
    (
        'assert john.salary_deduction == Decimal("2451.92")',
        'assert john.salary_deduction == Decimal("4250.00")'
    )
])
