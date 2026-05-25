"""
PDF to Markdown Converter
--------------------------
Converts a text-based PDF (e.g. resume, report) into a well-formatted Markdown file.
Uses pdfplumber for layout-aware extraction and Claude AI for intelligent MD formatting.

Usage:
    uv run pdf_to_md.py <input.pdf> [output.md]

Examples:
    uv run pdf_to_md.py resume.pdf
    uv run pdf_to_md.py resume.pdf my_resume.md
    uv run pdf_to_md.py report.pdf output/report.md

Requirements:
    - Copy .env.example to .env and set your ANTHROPIC_API_KEY inside it.
    - Run `uv sync` once to install all dependencies, then use `uv run` normally.
"""

import sys
import os
import argparse
from pathlib import Path

from dotenv import load_dotenv


def load_api_key() -> str:
    """Load ANTHROPIC_API_KEY from .env file, then fall back to environment."""
    # Look for .env in the same directory as this script
    script_dir = Path(__file__).parent
    env_path = script_dir / ".env"

    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        print(f"      Loaded environment from: {env_path}")
    else:
        # Also try current working directory
        cwd_env = Path.cwd() / ".env"
        if cwd_env.exists():
            load_dotenv(dotenv_path=cwd_env)
            print(f"      Loaded environment from: {cwd_env}")
        else:
            print(f"      Warning: No .env file found at {env_path}")
            print(f"      Copy .env.example to .env and add your ANTHROPIC_API_KEY.")

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    if not api_key or api_key == "sk-ant-your-key-here":
        print("\nError: ANTHROPIC_API_KEY is not set or is still the placeholder value.")
        print(f"  1. Open {env_path}")
        print("  2. Replace 'sk-ant-your-key-here' with your actual Anthropic API key.")
        print("  Get a key at: https://console.anthropic.com/")
        sys.exit(1)

    return api_key


def extract_text_with_layout(pdf_path: str) -> str:
    """Extract text from PDF preserving layout information."""
    import pdfplumber

    print(f"[1/3] Extracting text from PDF: {pdf_path}")

    all_pages_text = []

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        print(f"      Found {total_pages} page(s)")

        for i, page in enumerate(pdf.pages, 1):
            # Extract words with position and font-size data
            words = page.extract_words(
                x_tolerance=3,
                y_tolerance=3,
                keep_blank_chars=False,
                use_text_flow=True,
                extra_attrs=["fontname", "size"],
            )

            if words:
                # Group words into lines by vertical position
                lines = []
                current_line_y = None
                current_line_words = []
                current_line_sizes = []

                for word in words:
                    word_y = round(word["top"], 1)
                    font_size = word.get("size", 12) or 12

                    if current_line_y is None or abs(word_y - current_line_y) > 5:
                        if current_line_words:
                            avg_size = sum(current_line_sizes) / len(current_line_sizes)
                            lines.append((avg_size, " ".join(current_line_words)))
                        current_line_y = word_y
                        current_line_words = [word["text"]]
                        current_line_sizes = [font_size]
                    else:
                        current_line_words.append(word["text"])
                        current_line_sizes.append(font_size)

                if current_line_words:
                    avg_size = sum(current_line_sizes) / len(current_line_sizes)
                    lines.append((avg_size, " ".join(current_line_words)))

                # Annotate each line with its font size so Claude can infer headings
                page_text = "\n".join(f"[size:{size:.0f}] {line}" for size, line in lines)
            else:
                # Fallback to plain text if word-level extraction fails
                page_text = page.extract_text(x_tolerance=3, y_tolerance=3) or ""

            if page_text.strip():
                all_pages_text.append(f"--- PAGE {i} ---\n{page_text}")

            print(f"      Page {i}/{total_pages} extracted")

    return "\n\n".join(all_pages_text)


def convert_to_markdown(raw_text: str, source_filename: str, api_key: str) -> str:
    """Use Claude API to intelligently convert extracted text to Markdown."""
    import anthropic

    print("[2/3] Converting to Markdown using Claude AI...")

    client = anthropic.Anthropic(api_key=api_key)

    system_prompt = """You are an expert document formatter. Your job is to convert raw extracted PDF text into clean, well-structured Markdown.

The input lines are prefixed with [size:N] where N is the font size in points. Use these hints to infer heading levels:
- Largest sizes  → # H1  (document title, person's name)
- Second largest → ## H2 (major sections: Experience, Education, Skills, etc.)
- Third level    → ### H3 (sub-sections: job titles, degree names, company names)
- Normal body    → regular paragraph text

Rules:
1. Reproduce ALL content — do not summarise, skip, or paraphrase anything.
2. Use proper Markdown: # ## ### for headings, **bold**, *italic*, - for bullet lists, | for tables where appropriate.
3. Preserve logical groupings and structure from the original document.
4. Strip [size:N] prefixes and --- PAGE N --- markers from your output.
5. Use a horizontal rule (---) only if the original clearly separates major sections with a visual divider.
6. For resumes: name as H1, sections (Experience/Education/Skills) as H2, job titles/companies as H3.
7. Dates, locations, and one-line metadata should stay on the same line as their heading.
8. Output ONLY the Markdown content — no preamble, no explanation, no code fences."""

    user_prompt = (
        f"Convert this extracted PDF text to clean Markdown.\n"
        f"Source file: {source_filename}\n\n"
        f"{raw_text}"
    )

    # Handle large documents by chunking
    max_chars = 180_000  # safe limit for claude-sonnet context
    if len(user_prompt) > max_chars:
        print(f"      Document is large ({len(raw_text):,} chars) — processing in chunks...")
        return _convert_large_document(client, raw_text, source_filename, system_prompt, max_chars)

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    return message.content[0].text


def _convert_large_document(
    client, raw_text: str, source_filename: str, system_prompt: str, max_chars: int
) -> str:
    """Split large documents into page-boundary chunks and process each."""
    pages = [p for p in raw_text.split("--- PAGE ") if p.strip()]

    chunks: list[list[str]] = []
    current_chunk: list[str] = []
    current_size = 0

    for page in pages:
        if current_size + len(page) > max_chars // 2 and current_chunk:
            chunks.append(current_chunk)
            current_chunk = [page]
            current_size = len(page)
        else:
            current_chunk.append(page)
            current_size += len(page)

    if current_chunk:
        chunks.append(current_chunk)

    print(f"      Split into {len(chunks)} chunk(s)")
    md_parts = []

    for i, chunk in enumerate(chunks, 1):
        print(f"      Processing chunk {i}/{len(chunks)}...")
        chunk_text = "\n\n".join(chunk)
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8096,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Convert this extracted PDF text to clean Markdown.\n"
                        f"Source file: {source_filename} (part {i} of {len(chunks)})\n\n"
                        f"{chunk_text}"
                    ),
                }
            ],
        )
        md_parts.append(message.content[0].text)

    return "\n\n".join(md_parts)


def main():
    parser = argparse.ArgumentParser(
        description="Convert a text-based PDF to a Markdown file.",
        epilog="Example: uv run pdf_to_md.py resume.pdf resume.md",
    )
    parser.add_argument("input_pdf", help="Path to the input PDF file")
    parser.add_argument(
        "output_md",
        nargs="?",
        default=None,
        help="Output Markdown file path (default: same name as PDF with .md extension)",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Also save a .raw.txt file with the extracted text before AI processing (for debugging)",
    )

    args = parser.parse_args()

    # Validate input file
    input_path = Path(args.input_pdf)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)
    if input_path.suffix.lower() != ".pdf":
        print(f"Warning: File does not have a .pdf extension: {input_path}")

    # Resolve output path
    output_path = Path(args.output_md) if args.output_md else input_path.with_suffix(".md")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print()
    print("PDF → Markdown Converter")
    print("=" * 40)
    print(f"Input:  {input_path}")
    print(f"Output: {output_path}")
    print("=" * 40)
    print()

    # Load API key from .env
    api_key = load_api_key()

    # Step 1: Extract text with layout hints
    raw_text = extract_text_with_layout(str(input_path))

    if not raw_text.strip():
        print("\nError: No text could be extracted from the PDF.")
        print("This tool only works with text-based PDFs, not scanned/image PDFs.")
        sys.exit(1)

    if args.raw:
        raw_path = output_path.with_suffix(".raw.txt")
        raw_path.write_text(raw_text, encoding="utf-8")
        print(f"      Raw text saved → {raw_path}")

    # Step 2: Convert with Claude
    markdown_content = convert_to_markdown(raw_text, input_path.name, api_key)

    # Step 3: Write output
    print(f"[3/3] Saving Markdown → {output_path}")
    output_path.write_text(markdown_content, encoding="utf-8")

    line_count = len(markdown_content.splitlines())
    word_count = len(markdown_content.split())
    print(f"\n✓ Done!  ({line_count} lines, ~{word_count} words)")
    print(f"  Output: {output_path.resolve()}")


if __name__ == "__main__":
    main()