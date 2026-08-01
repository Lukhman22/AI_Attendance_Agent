import os
import re

directories = ['frontend/src/pages', 'frontend/src/components']
for directory in directories:
    for root, _, files in os.walk(directory):
        for file in files:
            if not file.endswith('.tsx'): continue
            path = os.path.join(root, file)
            with open(path, 'r') as f:
                content = f.read()
            
            # Simple replacements for known variables from API
            content = content.replace('records.map(r =>', '(records || []).map(r =>')
            content = content.replace('emps.find(e =>', '(emps || []).find(e =>')
            content = content.replace('employees.find((e) =>', '(employees || []).find((e) =>')
            content = content.replace('employees.find(e =>', '(employees || []).find(e =>')
            content = content.replace('employees.map((e) =>', '(employees || []).map((e) =>')
            content = content.replace('stats.map((s) =>', '(stats || []).map((s) =>')
            content = content.replace('payroll.map((p) =>', '(payroll || []).map((p) =>')
            content = content.replace('payroll.filter((p) =>', '(payroll || []).filter((p) =>')
            content = content.replace('annotations.find(a =>', '(annotations || []).find(a =>')
            content = content.replace('stats.reduce(', '(stats || []).reduce(')
            content = content.replace('payroll.reduce(', '(payroll || []).reduce(')
            
            with open(path, 'w') as f:
                f.write(content)
print("done")
