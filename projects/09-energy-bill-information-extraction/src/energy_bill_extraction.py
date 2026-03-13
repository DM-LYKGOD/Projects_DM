import argparse
import json
import os
from pathlib import Path

import pdfplumber
import pytesseract
from groq import Groq
from pdf2image import convert_from_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
ARTIFACTS_DIR.mkdir(exist_ok=True)


def extract_text_from_pdf(pdf_path: Path) -> dict[str, str]:
    extracted_pages: dict[str, str] = {}
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for index, page in enumerate(pdf.pages, start=1):
                text = page.extract_text()
                extracted_pages[f"Page {index}"] = text or "No text found."
    except Exception:
        images = convert_from_path(pdf_path)
        for index, image in enumerate(images, start=1):
            extracted_pages[f"Page {index}"] = pytesseract.image_to_string(image)
    return extracted_pages


def build_prompt(extracted_text: dict[str, str]) -> str:
    prompt = (
        "Extract the MPAN number, energy tariffs, and the total energy consumption "
        "from the following bill text. Return a concise structured summary.\n\n"
    )
    for page, text in extracted_text.items():
        prompt += f"{page}: {text}\n\n"
    return prompt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract structured information from an energy bill PDF.")
    parser.add_argument("pdf_path", type=Path, help="Path to the input PDF.")
    parser.add_argument(
        "--model",
        default="llama-3.3-70b-versatile",
        help="Groq model to use for the extraction summary."
    )
    parser.add_argument(
        "--text-output",
        type=Path,
        default=ARTIFACTS_DIR / "extracted_text.json",
        help="Where to save extracted page text."
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=ARTIFACTS_DIR / "energy_bill_summary.txt",
        help="Where to save the LLM summary."
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    pdf_path = args.pdf_path.resolve()
    if not pdf_path.exists():
        raise FileNotFoundError(f"Input PDF not found: {pdf_path}")

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError("Set GROQ_API_KEY before running this script.")

    extracted_text = extract_text_from_pdf(pdf_path)
    args.text_output.parent.mkdir(parents=True, exist_ok=True)
    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    args.text_output.write_text(json.dumps(extracted_text, indent=2), encoding="utf-8")

    client = Groq(api_key=api_key)
    prompt = build_prompt(extracted_text)
    response = client.chat.completions.create(
        model=args.model,
        messages=[{"role": "user", "content": prompt}],
    )
    summary = response.choices[0].message.content
    args.summary_output.write_text(summary, encoding="utf-8")
    print(summary)


if __name__ == "__main__":
    main()
