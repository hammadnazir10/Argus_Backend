"""File upload utilities and constants."""

from typing import Tuple


# File size limits (in bytes)
MAX_BOM_FILE_SIZE: int = 50 * 1024 * 1024  # 50 MB
MAX_QUOTE_FILE_SIZE: int = 20 * 1024 * 1024  # 20 MB

# Allowed file extensions
ALLOWED_BOM_EXTENSIONS: Tuple[str, ...] = ("xlsm", "xlsx")
ALLOWED_QUOTE_EXTENSIONS: Tuple[str, ...] = ("pdf", "xlsx", "xlsm", "csv")

# MIME types mapping for file validation
MIME_TYPES = {
    "xlsm": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xls": "application/vnd.ms-excel",
    "pdf": "application/pdf",
    "csv": "text/csv",
}

# Magic numbers (file signatures) for validation
MAGIC_NUMBERS = {
    "xlsm": [b"PK\x03\x04"],  # ZIP-based format
    "xlsx": [b"PK\x03\x04"],  # ZIP-based format
    "xls": [b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"],  # OLE2 format
    "pdf": [b"%PDF"],
    "csv": [],  # CSV has no fixed signature, text-based
}


def validate_file_extension(filename: str, allowed_extensions: Tuple[str, ...]) -> bool:
    """
    Validate file extension.
    
    Args:
        filename: The filename to validate
        allowed_extensions: Tuple of allowed extensions (without dot)
        
    Returns:
        True if file extension is allowed, False otherwise
    """
    if not filename:
        return False
    
    # Get extension without dot
    file_ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    
    return file_ext in allowed_extensions


def validate_file_size(file_size: int, max_size: int) -> bool:
    """
    Validate file size.
    
    Args:
        file_size: Size of the file in bytes
        max_size: Maximum allowed size in bytes
        
    Returns:
        True if file size is within limit, False otherwise
    """
    return 0 < file_size <= max_size


def validate_bom_file(filename: str, file_size: int) -> Tuple[bool, str]:
    """
    Validate BOM file (extension and size).
    
    Args:
        filename: Name of the BOM file
        file_size: Size of the file in bytes
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not validate_file_extension(filename, ALLOWED_BOM_EXTENSIONS):
        return False, f"Invalid BOM file format. Allowed: {', '.join(ALLOWED_BOM_EXTENSIONS)}"
    
    if not validate_file_size(file_size, MAX_BOM_FILE_SIZE):
        max_size_mb = MAX_BOM_FILE_SIZE / (1024 * 1024)
        return False, f"BOM file exceeds size limit ({max_size_mb}MB)"
    
    return True, ""


def validate_quote_file(filename: str, file_size: int) -> Tuple[bool, str]:
    """
    Validate quote file (extension and size).
    
    Args:
        filename: Name of the quote file
        file_size: Size of the file in bytes
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not validate_file_extension(filename, ALLOWED_QUOTE_EXTENSIONS):
        return False, f"Invalid quote file format. Allowed: {', '.join(ALLOWED_QUOTE_EXTENSIONS)}"
    
    if not validate_file_size(file_size, MAX_QUOTE_FILE_SIZE):
        max_size_mb = MAX_QUOTE_FILE_SIZE / (1024 * 1024)
        return False, f"Quote file exceeds size limit ({max_size_mb}MB)"
    
    return True, ""


def get_file_extension(filename: str) -> str:
    """
    Get file extension from filename.
    
    Args:
        filename: The filename
        
    Returns:
        Extension without dot, lowercase
    """
    if not filename or "." not in filename:
        return ""
    
    return filename.rsplit(".", 1)[-1].lower()


def get_mime_type(filename: str) -> str:
    """
    Get MIME type for a file.
    
    Args:
        filename: The filename
        
    Returns:
        MIME type or empty string if unknown
    """
    ext = get_file_extension(filename)
    return MIME_TYPES.get(ext, "application/octet-stream")


def validate_magic_number(file_bytes: bytes, filename: str) -> bool:
    """
    Validate file by checking magic number (file signature).
    
    Args:
        file_bytes: First few bytes of the file
        filename: The filename (to determine expected signature)
        
    Returns:
        True if magic number matches or no signature required, False otherwise
    """
    ext = get_file_extension(filename)
    
    if ext not in MAGIC_NUMBERS:
        return True  # Unknown extension, allow through
    
    signatures = MAGIC_NUMBERS[ext]
    
    # Some formats like CSV don't have fixed signatures
    if not signatures:
        return True
    
    # Check if file starts with any valid signature for this format
    for signature in signatures:
        if file_bytes.startswith(signature):
            return True
    
    return False


# File upload constants
UPLOAD_CHUNK_SIZE = 1024 * 1024  # 1 MB chunks for streaming
DEFAULT_TIMEOUT = 300  # 5 minutes
PRESIGNED_URL_EXPIRY = 900  # 15 minutes
MAX_CONCURRENT_UPLOADS = 15


def validate_file_magic_number(file_bytes: bytes, file_ext: str) -> bool:
    """
    Validate file by checking magic number (file signature).
    
    Args:
        file_bytes: File content bytes
        file_ext: File extension (without dot)
        
    Returns:
        True if magic number matches expected signature, False otherwise
    """
    if file_ext not in MAGIC_NUMBERS:
        return True  # Unknown extension, allow through
    
    signatures = MAGIC_NUMBERS[file_ext]
    
    # Some formats like CSV don't have fixed signatures
    if not signatures:
        return True
    
    # Check if file starts with any valid signature for this format
    for signature in signatures:
        if file_bytes.startswith(signature):
            return True
    
    return False


def validate_bom_columns(file_path: str) -> int:
    """
    Validate BOM file has required columns and return row count.
    
    Args:
        file_path: Path to the BOM file
        
    Returns:
        Number of data rows in the BOM file
        
    Raises:
        ValueError: If required columns are missing or file is invalid
    """
    try:
        import pandas as pd
        
        # Read Excel file
        df = pd.read_excel(file_path, engine='openpyxl')
        
        # Required columns for BOM validation
        required_columns = ['Size', 'Description', 'Manufacturer', 'Count']
        
        # Check for required columns (case-insensitive)
        df_columns = [col.strip().lower() for col in df.columns]
        missing_columns = []
        
        for req_col in required_columns:
            if req_col.lower() not in df_columns:
                missing_columns.append(req_col)
        
        if missing_columns:
            raise ValueError(f"BOM file missing required columns: {', '.join(missing_columns)}")
        
        # Return number of data rows (excluding header)
        return len(df)
        
    except pd.errors.EmptyDataError:
        raise ValueError("BOM file is empty")
    except pd.errors.ParserError as e:
        raise ValueError(f"BOM file format is invalid: {str(e)}")
    except Exception as e:
        raise ValueError(f"BOM file validation error: {str(e)}")


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe storage.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename with special characters replaced
    """
    import re
    
    if not filename:
        return "unnamed_file"
    
    # Keep only alphanumeric, dots, dashes, and underscores
    sanitized = re.sub(r'[^a-zA-Z0-9\.\-_]', '_', filename)
    
    # Remove multiple consecutive dots or underscores
    sanitized = re.sub(r'[_]{2,}', '_', sanitized)
    sanitized = re.sub(r'[\.]{2,}', '.', sanitized)
    
    # Ensure filename doesn't start with dot
    if sanitized.startswith('.'):
        sanitized = 'file' + sanitized
    
    # Limit filename length
    if len(sanitized) > 100:
        name, ext = sanitized.rsplit('.', 1) if '.' in sanitized else (sanitized, '')
        sanitized = name[:90] + ('.' + ext if ext else '')
    
    return sanitized
