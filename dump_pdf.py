import fitz
import sys

def main(pdf_path):
    doc = fitz.open(pdf_path)
    for i, page in enumerate(doc):
        print(f"--- Page {i+1} ---")
        blocks = page.get_text("blocks")
        for b in blocks:
            # block structure: (x0, y0, x1, y1, text, block_no, block_type)
            if b[6] == 0:  # text block
                text = b[4].strip()
                if text:
                    print(f"Block at ({b[0]:.1f}, {b[1]:.1f}) -> {repr(text)}")
        if i >= 1: # just first 2 pages
            break

if __name__ == "__main__":
    main("uploads/monthperformance23072026121726.pdf")
