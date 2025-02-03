import os

def ensure_prefix(output_path: str, asset_type: AssetType) -> str:
    """Ensure the output file has the correct prefix for its type."""
    dir_name = os.path.dirname(output_path)
    base_name = os.path.basename(output_path)
    
    # Remove any existing asset prefix
    for prefix in ['BK', 'GC', 'GL', 'SS']:
        if base_name.startswith(prefix):
            base_name = base_name[2:]
            break
    
    return os.path.join(dir_name, f"{asset_type.prefix}{base_name}")

def ensure_extension(path: str, fmt: str) -> str:
    """Ensure the output path has the correct extension."""
    base, ext = os.path.splitext(path)
    return f"{base}.{fmt.lower()}" 