class AssetError(Exception):
    """Base exception for all asset-related errors"""
    pass

class ImageFormatError(AssetError):
    """Raised when an unsupported image format is encountered"""
    def __init__(self, format: str):
        super().__init__(f"Unsupported image format: {format}. Supported formats are PNG, JPG, and WebP.")

class DLLError(AssetError):
    """Raised when there are issues with the Aurora DLL"""
    def __init__(self, message: str):
        super().__init__(f"DLL Error: {message}\n"
                        "Please ensure:\n"
                        "1. The AuroraAsset.dll file is present\n"
                        "2. The DLL architecture matches your Python installation\n"
                        "3. The DLL is not blocked by your system")

class AssetFileError(AssetError):
    """Raised when there are issues with the asset file format"""
    def __init__(self, message: str):
        super().__init__(f"Asset File Error: {message}\n"
                        "The asset file may be corrupted or in an unsupported format.")

class AssetTypeError(AssetError):
    """Raised when an invalid asset type is specified"""
    def __init__(self, asset_type: int):
        super().__init__(f"Invalid asset type: {asset_type}. "
                        "Valid types are 0 (Icon), 1 (Banner), 2 (Boxart), 4 (Background)")

class CompressionError(AssetError):
    """Raised when there are issues with image compression"""
    def __init__(self, message: str):
        super().__init__(f"Compression Error: {message}") 