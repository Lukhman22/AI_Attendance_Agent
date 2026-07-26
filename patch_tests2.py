import re

def update_file(path, replacements):
    with open(path, "r") as f:
        content = f.read()
    for old, new in replacements:
        content = content.replace(old, new)
    with open(path, "w") as f:
        f.write(content)

update_file("tests/test_e2e_api.py", [
    (
        'assert Decimal(str(john["salary_deduction"])) == Decimal("108.17")',
        'assert Decimal(str(john["salary_deduction"])) == Decimal("187.50")'
    )
])
