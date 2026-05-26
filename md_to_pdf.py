"""
Markdown to PDF Converter
--------------------------
Converts a Markdown file into a clean, well-formatted PDF.
Uses markdown-it-py to parse Markdown and xhtml2pdf to render it to PDF.
Pure Python — no system libraries (GTK etc.) required.

Usage:
    uv run md_to_pdf.py <input.md> [output.pdf]

Examples:
    uv run md_to_pdf.py resume.md
    uv run md_to_pdf.py resume.md my_resume.pdf
    uv run md_to_pdf.py notes/report.md output/report.pdf
"""

import sys
import argparse
from pathlib import Path
from io import BytesIO


# ── HTML template ─────────────────────────────────────────────────────────────

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8"/>
<style>
  @page {{
    size: A4;
    margin: 2.2cm 2.5cm 2.2cm 2.5cm;
  }}

  body {{
    font-family: Helvetica, Arial, sans-serif;
    font-size: 10.5pt;
    line-height: 1.6;
    color: #1a1a1a;
  }}

  h1 {{
    font-size: 20pt;
    color: #111;
    border-bottom: 2px solid #333;
    padding-bottom: 3pt;
    margin-top: 0;
    margin-bottom: 6pt;
  }}
  h2 {{
    font-size: 13pt;
    color: #222;
    border-bottom: 1px solid #bbb;
    padding-bottom: 2pt;
    margin-top: 16pt;
    margin-bottom: 4pt;
  }}
  h3 {{
    font-size: 11pt;
    color: #333;
    margin-top: 10pt;
    margin-bottom: 2pt;
  }}
  h4, h5, h6 {{
    font-size: 10pt;
    color: #444;
    margin-top: 8pt;
    margin-bottom: 2pt;
  }}

  p {{
    margin: 0 0 6pt 0;
  }}

  ul, ol {{
    margin: 3pt 0 7pt 0;
    padding-left: 18pt;
  }}
  li {{
    margin-bottom: 2pt;
  }}

  hr {{
    border: none;
    border-top: 1px solid #ddd;
    margin: 12pt 0;
  }}

  code {{
    font-family: Courier, monospace;
    font-size: 9pt;
    background: #f4f4f4;
    border: 1px solid #e0e0e0;
    padding: 1px 4px;
  }}

  pre {{
    background: #f6f6f6;
    border: 1px solid #ddd;
    border-left: 3px solid #555;
    padding: 7pt 9pt;
    margin: 7pt 0;
    font-family: Courier, monospace;
    font-size: 8.5pt;
    white-space: pre-wrap;
    word-wrap: break-word;
  }}
  pre code {{
    background: none;
    border: none;
    padding: 0;
  }}

  blockquote {{
    border-left: 3px solid #aaa;
    margin: 7pt 0 7pt 8pt;
    padding: 3pt 9pt;
    color: #555;
    font-style: italic;
  }}

  table {{
    border-collapse: collapse;
    width: 100%;
    margin: 9pt 0;
    font-size: 9.5pt;
  }}
  th {{
    background: #333333;
    color: #ffffff;
    font-weight: bold;
    padding: 4pt 7pt;
    text-align: left;
    border: 1px solid #333;
  }}
  td {{
    padding: 4pt 7pt;
    border: 1px solid #ccc;
  }}
  tr.even td {{
    background: #f9f9f9;
  }}

  a {{
    color: #0066cc;
  }}

  strong {{ font-weight: bold; }}
  em {{ font-style: italic; }}
  del {{ text-decoration: line-through; color: #888; }}
</style>
</head>
<body>
{content}
</body>
</html>"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def md_to_html(md_text: str) -> str:
    """Parse Markdown → HTML using markdown-it-py."""
    from markdown_it import MarkdownIt
    from mdit_py_plugins.front_matter import front_matter_plugin
    from mdit_py_plugins.deflist import deflist_plugin

    md = (
        MarkdownIt("commonmark", {"typographer": True})
        .enable("table")
        .enable("strikethrough")
        .use(front_matter_plugin)
        .use(deflist_plugin)
    )
    html = md.render(md_text)

    # xhtml2pdf doesn't support nth-child CSS; add class manually
    import re
    def stripe_table_rows(match):
        rows = match.group(0).split("<tr>")
        result = []
        even = False
        for part in rows:
            if part.strip().startswith("<td"):
                cls = ' class="even"' if even else ""
                result.append(f'<tr{cls}>' + part)
                even = not even
            else:
                result.append(part)
        return "".join(result)

    html = re.sub(r"<tbody>.*?</tbody>", stripe_table_rows, html, flags=re.DOTALL)
    return html


def html_to_pdf(html: str, output_path: Path) -> None:
    """Render HTML → PDF using xhtml2pdf (pure Python, no system deps)."""
    from xhtml2pdf import pisa

    buf = BytesIO()
    result = pisa.CreatePDF(html.encode("utf-8"), dest=buf, encoding="utf-8")

    if result.err:
        print(f"\nWarning: xhtml2pdf reported {result.err} error(s) during conversion.")
        print("The PDF may still have been created — check the output file.")

    output_path.write_bytes(buf.getvalue())


# ── Main conversion ───────────────────────────────────────────────────────────

def convert(input_path: Path, output_path: Path, save_html: bool = False) -> None:
    print()
    print("Markdown → PDF Converter")
    print("=" * 40)
    print(f"Input:  {input_path}")
    print(f"Output: {output_path}")
    print("=" * 40)
    print()

    print("[1/3] Reading Markdown...")
    md_text = input_path.read_text(encoding="utf-8")
    print(f"      {len(md_text.splitlines())} lines read")

    print("[2/3] Rendering Markdown → HTML...")
    body_html = md_to_html(md_text)
    full_html = HTML_TEMPLATE.format(content=body_html)

    if save_html:
        html_path = output_path.with_suffix(".html")
        html_path.write_text(full_html, encoding="utf-8")
        print(f"      Intermediate HTML saved → {html_path}")

    print("[3/3] Converting HTML → PDF...")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    html_to_pdf(full_html, output_path)

    size_kb = output_path.stat().st_size // 1024
    print(f"\n✓ Done!  ({size_kb} KB)")
    print(f"  Output: {output_path.resolve()}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert a Markdown file to a PDF.",
        epilog="Example: uv run md_to_pdf.py resume.md resume.pdf",
    )
    parser.add_argument("input_md", help="Path to the input Markdown (.md) file")
    parser.add_argument(
        "output_pdf",
        nargs="?",
        default=None,
        help="Output PDF path (default: same name as input with .pdf extension)",
    )
    parser.add_argument(
        "--html",
        action="store_true",
        help="Also save the intermediate .html file (useful for debugging styles)",
    )

    args = parser.parse_args()

    input_path = Path(args.input_md)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)

    output_path = Path(args.output_pdf) if args.output_pdf else input_path.with_suffix(".pdf")
    convert(input_path, output_path, save_html=args.html)


if __name__ == "__main__":
    main()