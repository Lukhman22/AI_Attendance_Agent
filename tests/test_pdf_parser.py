import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO
from backend.app.attendance.pdf_parser import read_pdf_attendance
from backend.app.core.exceptions import ApplicationError

def create_mock_doc(pages_blocks):
    doc = MagicMock()
    pages = []
    for pb in pages_blocks:
        page = MagicMock()
        
        # We need to construct blocks where the 5th element (index 4) is the text, and 7th (index 6) is 0
        blocks = []
        for i, text in enumerate(pb):
            blocks.append((0, i*10, 100, i*10+10, text, i, 0))
        page.get_text.return_value = blocks
        pages.append(page)
    
    doc.__iter__.return_value = iter(pages)
    return doc

@patch('backend.app.attendance.pdf_parser.fitz.open')
def test_valid_pdf(mock_fitz_open):
    mock_fitz_open.return_value = create_mock_doc([
        [
            "Report Month\nApril-2026",
            "Empcode\nE001\nName\nAlice Smith",
            "IN\n09:00\n10:00",
            "OUT\n17:00\n18:00",
            "STATUS\nP\nP"
        ],
        [
            "Empcode\nE002\nName\nBob",
            "STATUS\nA\nA"
        ]
    ])
    records = read_pdf_attendance(BytesIO(b"dummy"), "test.pdf")
    assert len(records) == 4
    
    assert records[0].employee_code == "E001"
    assert records[0].status == "P"
    
    assert records[2].employee_code == "E002"
    assert records[2].status == "A"

@patch('backend.app.attendance.pdf_parser.fitz.open')
def test_empty_pdf(mock_fitz_open):
    mock_fitz_open.return_value = create_mock_doc([[]])
    with pytest.raises(ApplicationError, match="Unable to detect attendance tables."):
        read_pdf_attendance(BytesIO(b"dummy"), "test.pdf")

@patch('backend.app.attendance.pdf_parser.fitz.open')
def test_corrupted_pdf(mock_fitz_open):
    mock_fitz_open.side_effect = Exception("Corrupted")
    with pytest.raises(ApplicationError, match="not a supported biometric attendance report"):
        read_pdf_attendance(BytesIO(b"dummy"), "test.pdf")

@patch('backend.app.attendance.pdf_parser.fitz.open')
def test_missing_report_month(mock_fitz_open):
    mock_fitz_open.return_value = create_mock_doc([
        [
            "Empcode\nE001\nName\nAlice",
            "IN\n09:00",
            "OUT\n17:00",
            "STATUS\nP"
        ]
    ])
    with pytest.raises(ApplicationError, match="Employee section is incomplete"):
        read_pdf_attendance(BytesIO(b"dummy"), "test.pdf")

@patch('backend.app.attendance.pdf_parser.fitz.open')
def test_malformed_employee_skip(mock_fitz_open):
    mock_fitz_open.return_value = create_mock_doc([
        [
            "Report Month\nApril-2026",
            "Empcode\nE001\nName\nAlice",
            "IN\n09:00",
            "OUT\n17:00",
            "STATUS\nP",
            "Empcode\nE002", # Missing name
            "STATUS\nP",
            "Empcode\nE003\nName\nCharlie",
            "STATUS\nP",
        ]
    ])
    records = read_pdf_attendance(BytesIO(b"dummy"), "test.pdf")
    assert len(records) == 2
    assert records[0].employee_code == "E001"
    assert records[1].employee_code == "E003"
