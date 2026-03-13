# Energy Bill Information Extraction

## Overview

Command-line Python workflow for extracting structured information from energy bills using PDF text extraction, OCR fallback, and an LLM prompt.

## Stack

- Python
- `pdfplumber`
- `pdf2image`
- `pytesseract`
- `groq`

## Notes

- API credentials must be provided through the `GROQ_API_KEY` environment variable.
- Sample input PDFs are not committed in this repository.
- Extracted text and final summaries are written to `artifacts/`.

## Run

```bash
python src/energy_bill_extraction.py path/to/bill.pdf
```
