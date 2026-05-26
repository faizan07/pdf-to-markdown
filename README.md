# PDF ↔ Markdown Converter

Two-way converter between PDF and Markdown using Claude AI.

| Script | Direction |
|---|---|
| `pdf_to_md.py` | PDF → Markdown (uses Claude AI) |
| `md_to_pdf.py` | Markdown → PDF (fully local, no API needed) |

## Setup

**1. Install dependencies**
```powershell
uv sync
```

> **Windows note for WeasyPrint:** WeasyPrint needs GTK libraries on Windows.
> Download and run the GTK3 installer from https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases
> then restart your terminal before running `uv sync`.

**2. Add your API key** *(only needed for `pdf_to_md.py`)*
```powershell
copy .env.example .env
# Open .env and replace the placeholder with your real key from https://console.anthropic.com/
```

## Usage

### PDF → Markdown
```powershell
uv run pdf_to_md.py resume.pdf              # → resume.md
uv run pdf_to_md.py resume.pdf output.md    # custom output name
uv run pdf_to_md.py resume.pdf --raw        # also save raw extracted text
```

### Markdown → PDF
```powershell
uv run md_to_pdf.py resume.md               # → resume.pdf
uv run md_to_pdf.py resume.md output.pdf    # custom output name
uv run md_to_pdf.py resume.md --html        # also save intermediate HTML
```

## Project Structure

```
pdf_to_md/
├── pdf_to_md.py       # PDF → Markdown (Claude AI)
├── md_to_pdf.py       # Markdown → PDF (local, no API)
├── pyproject.toml     # All dependencies
├── .env               # Your API key (never commit this)
├── .env.example       # Template to commit
└── .gitignore
```

## Notes

- `pdf_to_md.py` works with **text-based PDFs** only (not scanned/image PDFs).
- `md_to_pdf.py` is fully offline — no API key required.
- Tables, code blocks, headings, bold/italic, and blockquotes are all styled in the PDF output.