def get_actual_pages_to_print(page_range_str: str, total_document_pages: int) -> int:
    """Parses a string like '1-3, 5' and returns the exact number of pages to print."""
    if not page_range_str or not page_range_str.strip():
        return total_document_pages
        
    pages = set()
    parts = page_range_str.replace(" ", "").split(",")
    
    for part in parts:
        if not part: continue
        if "-" in part:
            try:
                start_str, end_str = part.split("-")
                start_p = int(start_str)
                end_p = int(end_str)
                # Ensure start is smaller than end
                if start_p > end_p:
                    start_p, end_p = end_p, start_p
                # Add to set (prevents charging twice if customer types "1-3, 2-4")
                for p in range(start_p, end_p + 1):
                    if 1 <= p <= total_document_pages:
                        pages.add(p)
            except ValueError:
                pass # Ignore invalid text
        else:
            try:
                p = int(part)
                if 1 <= p <= total_document_pages:
                    pages.add(p)
            except ValueError:
                pass
                
    # If they typed gibberish, default to all pages
    return len(pages) if len(pages) > 0 else total_document_pages