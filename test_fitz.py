import fitz
import re

def parse_pdf(path):
    doc = fitz.open(path)
    
    # We will accumulate tokens/lines for each employee.
    employees = []
    current_emp = {}
    
    for page in doc:
        blocks = page.get_text("blocks")
        # sort blocks top to bottom, then left to right
        blocks.sort(key=lambda b: (b[1], b[0]))
        
        for b in blocks:
            if b[6] != 0: continue
            text = b[4].strip()
            if not text: continue
            
            # Global report month
            if "Report Month" in text:
                m = re.search(r'Report Month\s*([A-Za-z]+-\d{4})', text, re.IGNORECASE)
                if m:
                    print("Found Report Month:", m.group(1))
                    
            if "Empcode\n" in text or re.search(r'Empcode\s+', text, re.IGNORECASE):
                if "code" in current_emp:
                    employees.append(current_emp)
                current_emp = {"code": None, "name": None, "days": {}, "in": [], "out": [], "work": [], "break": [], "ot": [], "status": []}
                
                # Extract code and name from this block
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                for i, line in enumerate(lines):
                    if line.lower() == "empcode" and i + 1 < len(lines):
                        current_emp["code"] = lines[i+1]
                    if line.lower() == "name" and i + 1 < len(lines):
                        current_emp["name"] = lines[i+1]
            
            # Tabular columns
            tokens = re.split(r'\s+', text)
            if not tokens: continue
            header = tokens[0].upper()
            
            if header == "1" and tokens[-1].isdigit():
                # this is the day row
                pass
            elif header in ["IN", "OUT", "WORK", "BREAK", "OT", "STATUS"]:
                # The rest are values
                vals = tokens[1:]
                if header == "IN": current_emp["in"].extend(vals)
                if header == "OUT": current_emp["out"].extend(vals)
                if header == "WORK": current_emp["work"].extend(vals)
                if header == "BREAK": current_emp["break"].extend(vals)
                if header == "OT": current_emp["ot"].extend(vals)
                if header == "STATUS": current_emp["status"].extend(vals)

    if current_emp and "code" in current_emp:
        employees.append(current_emp)
        
    for e in employees:
        print(f"Emp: {e['code']} - {e['name']}")
        print(f" IN: {len(e['in'])} {e['in'][:3]}")
        print(f" OUT: {len(e['out'])} {e['out'][:3]}")
        print(f" WORK: {len(e['work'])} {e['work'][:3]}")
        print(f" STATUS: {len(e['status'])} {e['status'][:3]}")

parse_pdf("uploads/monthperformance23072026121726.pdf")
