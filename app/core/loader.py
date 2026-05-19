import fitz  # PyMuPDF
import docx
import pandas as pd
from pathlib import Path

def load_to_markdown(file_path: str, file_type: str) -> str:
    """
    Loads any file and converts it to
    clean Markdown format with page markers.
    Markdown is consistent, clean, and
    chunks beautifully.
    """
    if file_type == "pdf":
        return load_pdf_to_markdown(file_path)
    elif file_type == "docx":
        return load_docx_to_markdown(file_path)
    elif file_type == "csv":
        return load_csv_to_markdown(file_path)
    elif file_type in ["xlsx", "xls"]:
        return load_excel_to_markdown(file_path)
    elif file_type == "txt":
        return load_txt_to_markdown(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")


def load_pdf_to_markdown(file_path: str) -> str:
    """
    Converts PDF to Markdown page by page.
    Adds <!-- page:N --> markers for citations.
    Detects headings by font size.
    """
    doc = fitz.open(file_path)
    markdown = ""

    for page_num, page in enumerate(doc, start=1):
        markdown += f"\n<!-- page:{page_num} -->\n\n"

        blocks = page.get_text("dict")["blocks"]

        for block in blocks:
            if block["type"] == 0:  # text block
                for line in block["lines"]:
                    line_text = ""
                    font_size = 0

                    for span in line["spans"]:
                        line_text += span["text"]
                        font_size = max(font_size, span["size"])

                    line_text = line_text.strip()
                    if not line_text:
                        continue

                    # Detect headings by font size
                    if font_size >= 18:
                        markdown += f"# {line_text}\n\n"
                    elif font_size >= 14:
                        markdown += f"## {line_text}\n\n"
                    elif font_size >= 12:
                        markdown += f"### {line_text}\n\n"
                    else:
                        markdown += f"{line_text}\n\n"

    doc.close()
    return markdown.strip()


def load_docx_to_markdown(file_path: str) -> str:
    """
    Converts Word document to Markdown.
    Preserves headings, paragraphs, and tables.
    """
    document = docx.Document(file_path)
    markdown = ""

    for element in document.element.body:
        tag = element.tag.split("}")[-1]

        if tag == "p":
            # Paragraph
            para = docx.text.paragraph.Paragraph(element, document)
            text = para.text.strip()
            if not text:
                continue

            style = para.style.name.lower()

            if "heading 1" in style:
                markdown += f"# {text}\n\n"
            elif "heading 2" in style:
                markdown += f"## {text}\n\n"
            elif "heading 3" in style:
                markdown += f"### {text}\n\n"
            else:
                markdown += f"{text}\n\n"

        elif tag == "tbl":
            # Table
            table = docx.table.Table(element, document)
            markdown += convert_table_to_markdown(table)
            markdown += "\n\n"

    return markdown.strip()


def convert_table_to_markdown(table) -> str:
    """
    Converts a Word table to Markdown table format.
    Tables are kept as atomic units — never split mid-row.
    """
    rows = []

    for i, row in enumerate(table.rows):
        cells = [cell.text.strip() for cell in row.cells]
        rows.append("| " + " | ".join(cells) + " |")

        # Add separator after header row
        if i == 0:
            separator = "| " + " | ".join(
                ["---"] * len(cells)
            ) + " |"
            rows.append(separator)

    return "\n".join(rows)


def load_csv_to_markdown(file_path: str) -> str:
    """
    Converts CSV to Markdown format.
    Includes overview, statistics, and
    full data as Markdown table.
    """
    df = pd.read_csv(file_path)

    markdown = "# Dataset Overview\n\n"
    markdown += f"- **Total rows:** {len(df)}\n"
    markdown += f"- **Total columns:** {len(df.columns)}\n"
    markdown += f"- **Columns:** {', '.join(df.columns.tolist())}\n\n"

    markdown += "## Statistical Summary\n\n"
    markdown += df.describe().to_markdown()
    markdown += "\n\n"

    markdown += "## Full Data\n\n"
    markdown += df.to_markdown(index=False)

    return markdown


def load_excel_to_markdown(file_path: str) -> str:
    """
    Converts Excel to Markdown.
    Each sheet becomes its own section.
    """
    xl = pd.ExcelFile(file_path)
    markdown = ""

    for sheet_name in xl.sheet_names:
        df = pd.read_excel(file_path, sheet_name=sheet_name)

        markdown += f"# Sheet: {sheet_name}\n\n"
        markdown += f"- **Rows:** {len(df)}\n"
        markdown += f"- **Columns:** {', '.join(df.columns.tolist())}\n\n"
        markdown += df.to_markdown(index=False)
        markdown += "\n\n"

    return markdown.strip()


def load_txt_to_markdown(file_path: str) -> str:
    """
    Plain text — minimal conversion needed.
    Just clean up and return.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read().strip()

    # Add basic structure if none exists
    lines = text.split("\n")
    markdown = ""

    for line in lines:
        line = line.strip()
        if not line:
            markdown += "\n"
        else:
            markdown += f"{line}\n"

    return markdown


def get_file_type(filename: str) -> str:
    """
    Returns file type from filename extension.
    """
    extension = Path(filename).suffix.lower().replace(".", "")

    supported = {
        "pdf": "pdf",
        "docx": "docx",
        "doc": "docx",
        "csv": "csv",
        "xlsx": "xlsx",
        "xls": "xls",
        "txt": "txt",
    }

    if extension not in supported:
        raise ValueError(
            f"Unsupported file: .{extension}. "
            f"Supported: PDF, DOCX, CSV, Excel, TXT"
        )

    return supported[extension]