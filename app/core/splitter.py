from typing import List
# NEW: LangChain moved these to a separate package
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

def split_markdown(text: str, file_type: str) -> List[str]:
    """
    Splits clean Markdown into meaningful chunks.
    Uses headers as natural boundaries first, 
    then falls back to size-based splitting.
    """

    # Step 1 — Split on Markdown headers first
    # This keeps sections together naturally
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("#", "heading1"),
            ("##", "heading2"),
            ("###", "heading3"),
        ],
        strip_headers=False,
    )

    header_chunks = header_splitter.split_text(text)

    # Step 2 — Define splitting logic based on file type
    if file_type in ["csv", "xlsx", "xls"]:
        chunk_size = 1500
        chunk_overlap = 200
    elif file_type == "pdf":
        chunk_size = 1000
        chunk_overlap = 150
    else:
        chunk_size = 800
        chunk_overlap = 100

    char_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""],
    )

    # Step 3 — Combine both splitting strategies
    final_chunks = []

    for header_chunk in header_chunks:
        content = header_chunk.page_content
        
        # If the header section is too large, split it further
        if len(content) > chunk_size:
            sub_chunks = char_splitter.split_text(content)
            final_chunks.extend(sub_chunks)
        else:
            final_chunks.append(content)

    # Step 4 — Clean up
    # Remove empty chunks and very short fragments (noise)
    cleaned_chunks = [
        c.strip() for c in final_chunks 
        if c.strip() and len(c.strip()) > 50
    ]

    return cleaned_chunks