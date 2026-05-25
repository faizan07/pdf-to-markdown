# PDF to Markdown Converter

Converts a text-based PDF (resume, report, article) into a clean, well-formatted Markdown file using Claude AI.

## Setup

**1. Install dependencies**
```powershell
uv sync
```

**2. Add your API key**
```powershell
# Copy the example env file
copy .env.example .env
```
Then open `.env` and replace `sk-ant-your-key-here` with your actual key from [console.anthropic.com](https://console.anthropic.com/).

## Usage

```powershell
# Output auto-named: resume.pdf → resume.md
uv run pdf_to_md.py resume.pdf

# Specify output file
uv run pdf_to_md.py resume.pdf my_resume.md

# Also save raw extracted text (useful for debugging)
uv run pdf_to_md.py resume.pdf --raw
```

## Project Structure

```
pdf_to_md/
├── pdf_to_md.py       # Main script
├── pyproject.toml     # Dependencies & project metadata
├── .env               # Your API key (never commit this)
├── .env.example       # Template — commit this instead
└── .gitignore
```

## Notes

- Works with **text-based PDFs** only (not scanned/image PDFs).
- Font size metadata from the PDF is used to infer heading levels (H1/H2/H3).
- Large documents are automatically chunked to stay within API limits.