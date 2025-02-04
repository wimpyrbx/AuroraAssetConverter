import argparse
import os
from enum import IntEnum
from PIL import Image
import io
import struct
from ctypes import create_string_buffer, addressof, c_int, byref
from typing import Tuple, Optional, List
from AuroraDLL import AuroraDLL  # Using the DLL wrapper we created earlier
import re

class AssetType(IntEnum):
    Icon = 0
    Banner = 1
    Boxart = 2
    Slot = 3
    Background = 4
    Screenshot1 = 5
    Screenshot2 = 6
    Screenshot3 = 7
    Screenshot4 = 8
    Screenshot5 = 9
    Screenshot6 = 10
    Screenshot7 = 11
    Screenshot8 = 12
    Screenshot9 = 13
    Screenshot10 = 14
    Screenshot11 = 15
    Screenshot12 = 16
    Screenshot13 = 17
    Screenshot14 = 18
    Screenshot15 = 19
    Screenshot16 = 20
    Screenshot17 = 21
    Screenshot18 = 22
    Screenshot19 = 23
    Screenshot20 = 24
    ScreenshotStart = 5
    ScreenshotEnd = 24
    Max = 24

    @property
    def required_dimensions(self) -> Tuple[int, int]:
        """Get required dimensions for each asset type"""
        dimensions = {
            AssetType.Icon: (64, 64),
            AssetType.Banner: (420, 96),
            AssetType.Boxart: (900, 600),
            AssetType.Slot: (128, 128),  # Add slot dimensions
            AssetType.Background: (1280, 720),
            # Screenshots use the same dimensions
        }
        return dimensions.get(self, (1000, 562))  # Default to screenshot size

class AssetError(Exception):
    """Base exception for all asset-related errors"""
    pass

class ImageProcessingError(AssetError):
    """Raised when image processing fails"""
    pass

class AssetConversionError(AssetError):
    """Raised when asset conversion fails"""
    pass

class AuroraAssetFile:
    MAGIC = 0x52584541  # 'AXER' in ASCII
    VERSION = 1
    HEADER_SIZE = 20
    ENTRY_SIZE = 64
    ALIGNMENT = 2048

    def __init__(self, dll_path=".\AuroraAsset.dll", verbose=False):
        self.verbose = verbose
        self.auto_resize = True  # Add auto-resize flag, default to True
        try:
            self.converter = AuroraDLL(dll_path)
        except Exception as e:
            print(f"Failed to initialize converter: {e}")
            print(" Please ensure:")
            print("1. The AuroraAsset.dll file is in the same directory as the script")
            print("2. You're using the correct version (32/64-bit) of the DLL for your Python installation")
            print("3. The DLL is accessible and not blocked by your system")
            raise
        self.flags = 0
        self.screenshot_count = 0
        self.entries = [{'offset': 0, 'size': 0, 'texture_header': bytearray(52), 'video_data': bytearray()} 
                       for _ in range(AssetType.Max + 1)]
        
    def _swap_uint32(self, value: int) -> int:
        return struct.unpack(">I", struct.pack("<I", value))[0]

    def _calculate_data_offset(self) -> int:
        offset = self.HEADER_SIZE + (len(self.entries) * self.ENTRY_SIZE)
        return offset + (self.ALIGNMENT - (offset % self.ALIGNMENT))

    def _update_screenshot_count(self) -> None:
        """Update screenshot count based on valid screenshot entries"""
        max_screenshot = 0
        for i in range(AssetType.ScreenshotStart, AssetType.ScreenshotEnd + 1):
            if len(self.entries[i]['video_data']) > 0:
                max_screenshot = max(max_screenshot, i - AssetType.ScreenshotStart + 1)
        self.screenshot_count = max_screenshot

    def import_image(self, image_path: str, asset_type: AssetType, compression: bool = True, verbose: bool = False) -> bool:
        try:
            if not os.path.exists(image_path):
                raise ImageProcessingError(f"Image file not found: {image_path}")
            # Open and convert image to RGBA
            with Image.open(image_path) as img:
                # Auto-resize logic
                if self.auto_resize:
                    if asset_type == AssetType.Boxart:
                        new_size = (900, 600)
                    elif asset_type == AssetType.Background:
                        new_size = (1280, 720)
                    elif asset_type in [AssetType.Icon, AssetType.Banner]:
                        new_size = (64, 64) if asset_type == AssetType.Icon else (420, 96)
                    elif AssetType.ScreenshotStart <= asset_type <= AssetType.ScreenshotEnd:
                        new_size = (1000, 562)
                    else:
                        new_size = img.size  # Default to original size if type not matched
                    
                    if img.size != new_size:
                        img = img.resize(new_size, Image.Resampling.LANCZOS)
                        if verbose:
                            print(f"Resized image from {img.size} to {new_size}")

                # Convert to RGBA if not already in that mode
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')

                # Convert to raw ARGB bytes
                raw_bytes = bytearray()
                for y in range(img.height):
                    for x in range(img.width):
                        r, g, b, a = img.getpixel((x, y))
                        raw_bytes.extend([a, r, g, b])  # ARGB format

                # Convert to asset format
                success, header, video = self.converter.process_image_to_asset(
                    bytes(raw_bytes), img.width, img.height, compression
                )
                
                if success:
                    # Set entry index and flags based on asset type
                    entry_idx = asset_type.value
                    if asset_type == AssetType.Boxart:
                        self.flags |= 0x04  # Set boxart flag
                    elif asset_type == AssetType.Background:
                        self.flags |= 0x10  # Set background flag
                    elif asset_type in [AssetType.Icon, AssetType.Banner]:
                        self.flags |= 0x01  # Set icon/banner flag
                    elif AssetType.ScreenshotStart <= asset_type <= AssetType.ScreenshotEnd:
                        self.flags |= (1 << asset_type.value)
                        self._update_screenshot_count()

                    # Store the data
                    self.entries[entry_idx]['texture_header'] = bytearray(header)
                    self.entries[entry_idx]['video_data'] = bytearray(video)
                    if verbose:
                        print(f"Successfully imported {asset_type.name} to entry {entry_idx}")
                return success
        except Exception as e:
            raise AssetConversionError(f"Failed to import image: {str(e)}")

    def save_asset(self, output_path: str, verbose: bool = False) -> bool:
        try:
            with open(output_path, 'wb') as f:
                # Write header
                data_size = sum(len(entry['video_data']) for entry in self.entries)
                f.write(struct.pack('>I', self.MAGIC))  # AXER in big-endian
                f.write(struct.pack('<I', self.VERSION))
                f.write(struct.pack('<I', data_size))
                f.write(struct.pack('<I', self.flags))
                f.write(struct.pack('<I', self.screenshot_count))

                # Write entry table (25 entries * 64 bytes)
                for entry in self.entries:
                    # Always write offset as 0 as seen in working files
                    f.write(struct.pack('<I', 0))  # Offset
                    f.write(struct.pack('<I', len(entry['video_data'])))  # Size
                    f.write(struct.pack('<I', 0))  # Extended info
                    f.write(entry['texture_header'])  # 52 bytes texture header

                # Write padding to align to 2048 bytes
                current_pos = f.tell()
                padding_size = 2048 - (current_pos % 2048)
                f.write(b'\x00' * padding_size)

                # Write actual texture data
                for entry in self.entries:
                    if len(entry['video_data']) > 0:
                        f.write(entry['video_data'])

                return True
        except Exception as e:
            raise AssetConversionError(f"Failed to save asset: {str(e)}")

    def extract_image(self, asset_path: str, asset_type: AssetType = AssetType.Icon) -> Optional[Image.Image]:
        try:
            with open(asset_path, 'rb') as f:
                data = f.read()

            if len(data) < self.ALIGNMENT:
                raise ValueError("Invalid asset file size")

            # Validate header
            magic = self._swap_uint32(struct.unpack('<I', data[0:4])[0])
            version = self._swap_uint32(struct.unpack('<I', data[4:8])[0])
            
            if magic != self.MAGIC:
                raise ValueError("Invalid asset file magic")
            if version != self.VERSION:
                raise ValueError("Unsupported asset file version")

            # Read entry table
            self.flags = self._swap_uint32(struct.unpack('<I', data[12:16])[0])
            self.screenshot_count = self._swap_uint32(struct.unpack('<I', data[16:20])[0])

            entry_offset = self.HEADER_SIZE + (asset_type * self.ENTRY_SIZE)
            offset = self._swap_uint32(struct.unpack('<I', data[entry_offset:entry_offset+4])[0])
            size = self._swap_uint32(struct.unpack('<I', data[entry_offset+4:entry_offset+8])[0])
            
            if size == 0:
                return None

            texture_header = data[entry_offset+12:entry_offset+64]
            data_offset = self._calculate_data_offset() + offset
            video_data = data[data_offset:data_offset+size]

            success, image_data, width, height = self.converter.process_asset_to_image(
                texture_header, video_data
            )

            if success:
                # Convert BGRA to RGBA
                img_array = bytearray(image_data)
                for i in range(0, len(img_array), 4):
                    img_array[i], img_array[i+1], img_array[i+2], img_array[i+3] = \
                        img_array[i+3], img_array[i+2], img_array[i+1], img_array[i]
                
                img = Image.frombytes('RGBA', (width, height), bytes(img_array))
                return img
            return None
        except Exception as e:
            print(f"Error extracting image: {e}")
            return None

    def validate_image_size(self, img: Image.Image, asset_type: AssetType) -> None:
        """Validate image dimensions for specific asset types"""
        width, height = img.size
        
        if asset_type == AssetType.Icon:
            if width != 64 or height != 64:
                raise ImageProcessingError(f"Icon must be 64x64 pixels, got {width}x{height}")
        elif asset_type == AssetType.Banner:
            if width != 420 or height != 96:
                raise ImageProcessingError(f"Banner must be 420x96 pixels, got {width}x{height}")
        elif asset_type == AssetType.Boxart:
            if width != 900 or height != 600:
                raise ImageProcessingError(f"Boxart must be 900x600 pixels, got {width}x{height}")
        elif asset_type == AssetType.Background:
            if width != 1280 or height != 720:
                raise ImageProcessingError(f"Background must be 1280x720 pixels, got {width}x{height}")
        elif AssetType.ScreenshotStart <= asset_type <= AssetType.ScreenshotEnd:
            if width != 1000 or height != 562:
                raise ImageProcessingError(f"Screenshots must be 1000x562 pixels, got {width}x{height}")

def ensure_prefix(output_path: str, asset_type: AssetType) -> str:
    """Ensure the output file has the correct prefix for its type."""
    dir_name = os.path.dirname(output_path)
    base_name = os.path.basename(output_path)
    
    # Remove any existing asset prefix
    for prefix in ['BK', 'GC', 'GL', 'SS']:
        if base_name.startswith(prefix):
            base_name = base_name[2:]
            break
    
    # Add correct prefix
    if asset_type == AssetType.Background:
        prefix = 'BK'
    elif asset_type == AssetType.Boxart:
        prefix = 'GC'
    elif asset_type in [AssetType.Icon, AssetType.Banner]:
        prefix = 'GL'
    elif AssetType.ScreenshotStart <= asset_type <= AssetType.ScreenshotEnd:
        prefix = 'SS'
    else:
        prefix = 'BK'  # Default to background
        
    return os.path.join(dir_name, f"{prefix}{base_name}")

def create_background_parser(subparsers):
    parser = subparsers.add_parser('background', help='Create background asset')
    parser.add_argument('image', help='Background image file')
    parser.add_argument('titleid', help='Title ID for the game')
    parser.set_defaults(func=handle_background)

def create_boxart_parser(subparsers):
    parser = subparsers.add_parser('boxart', help='Create boxart asset')
    parser.add_argument('image', help='Boxart image file')
    parser.add_argument('titleid', help='Title ID for the game')
    parser.set_defaults(func=handle_boxart)

def create_screenshots_parser(subparsers):
    parser = subparsers.add_parser('screenshots', help='Create screenshots asset')
    parser.add_argument('images', nargs='+', help='Screenshot image files')
    parser.add_argument('titleid', help='Title ID for the game')
    parser.set_defaults(func=handle_screenshots)

def create_bannericon_parser(subparsers):
    parser = subparsers.add_parser('bannericon', help='Create banner and icon asset')
    parser.add_argument('--banner', required=True, help='Banner image file')
    parser.add_argument('--icon', required=True, help='Icon image file')
    parser.add_argument('titleid', help='Title ID for the game')
    parser.set_defaults(func=handle_bannericon)

def create_folder_parser(subparsers):
    parser = subparsers.add_parser('folder', help='Process all assets in a folder')
    parser.add_argument('folder', help='Path to folder containing assets')
    parser.add_argument('titleid', help='Title ID for the game')
    parser.add_argument('--overwrite', action='store_true', default=False,
                      help='Overwrite existing asset files (default: False)')
    parser.set_defaults(func=handle_folder)

def create_extract_parser(subparsers):
    parser = subparsers.add_parser('extract', help='Extract images from an asset file')
    parser.add_argument('asset', help='Path to the asset file')
    parser.add_argument('format', choices=['png', 'webp'], help='Output image format')
    parser.set_defaults(func=handle_extract)

def handle_background(args):
    asset = AuroraAssetFile()
    if asset.import_image(args.image, AssetType.Background):
        output_path = f"BK{args.titleid}.asset"
        if asset.save_asset(output_path):
            # if verbose, print the full path else just the filename
            if args.verbose:
                print(f"Created background asset: {output_path}")
            else:
                print(f"Created background asset: {os.path.basename(output_path)}")
        else:
            print("Failed to save background asset")


    else:
        print("Failed to import background image")


def handle_boxart(args):
    asset = AuroraAssetFile(verbose=args.verbose)
    if args.verbose:
        print("Starting boxart conversion...")
    if asset.import_image(args.image, AssetType.Boxart, verbose=args.verbose):
        output_path = f"GC{args.titleid}.asset"
        if asset.save_asset(output_path, verbose=args.verbose):
            if args.verbose:
                print(f"Created boxart asset: {output_path}")
            else:
                print(f"Created boxart asset: {os.path.basename(output_path)}")
        else:
            print("Failed to save boxart asset")
    else:

        print("Failed to import boxart image")

def handle_screenshots(args):
    asset = AuroraAssetFile()
    for idx, image in enumerate(args.images):
        try:
            asset_type = AssetType(AssetType.Screenshot1 + idx)
            if not asset.import_image(image, asset_type):
                print(f"Failed to import screenshot {idx + 1}")
                return
        except ValueError:
            print(f"Error: Too many screenshots. Maximum is {AssetType.ScreenshotEnd - AssetType.ScreenshotStart + 1}")
            return
    
    output_path = f"SS{args.titleid}.asset"
    if asset.save_asset(output_path):
        if args.verbose:
            print(f"Created screenshots asset with {len(args.images)} screenshots: {output_path}")
        else:
            print(f"Created screenshots asset with {len(args.images)} screenshots: {os.path.basename(output_path)}")
    else:
        print("Failed to save screenshots asset")


def handle_bannericon(args):
    asset = AuroraAssetFile()
    
    # Import banner
    if not asset.import_image(args.banner, AssetType.Banner):
        print("Failed to import banner image")
        return
    
    # Import icon
    if not asset.import_image(args.icon, AssetType.Icon):
        print("Failed to import icon image")
        return
    
    output_path = f"GL{args.titleid}.asset"
    if asset.save_asset(output_path):
        if args.verbose:
            print(f"Created banner/icon asset: {output_path}")
        else:
            print(f"Created banner/icon asset: {os.path.basename(output_path)}")
    else:
        print("Failed to save banner/icon asset")


def handle_folder(args):
    # Strip trailing backslashes from the folder path
    folder_path = args.folder.rstrip('\\')
    process_folder(folder_path, args.titleid, verbose=args.verbose, overwrite=args.overwrite)

def process_folder(folder_path: str, titleid: str, verbose: bool = False, overwrite: bool = False):
    # Create output subfolder
    output_folder = os.path.join(folder_path, titleid)
    os.makedirs(output_folder, exist_ok=True)
    
    # Initialize assets_created flag
    assets_created = False
    
    # Function to check if we should process an asset
    def should_process_asset(prefix):
        output_path = os.path.join(output_folder, f"{prefix}{titleid}.asset")
        if not overwrite and os.path.exists(output_path):
            # if we are not overwriting but the file exists and is below 10kb we should process regardless of overwrite flag
            if os.path.getsize(output_path) < 10240 and verbose:
                print(f"Skipping {prefix} asset - file already exists but is below 10kb")
                return True
            if verbose:
                print(f"Skipping {prefix} asset - file already exists")
            return False
        return True

    # Function to find asset files
    def find_asset_file(base_name):
        # Try exact matches first
        for ext in ['png', 'webp', 'jpg']:  # Added JPG as last resort
            filename = f"{base_name}.{ext}"
            if filename in os.listdir(folder_path):
                return filename
        
        # Try numbered versions
        for ext in ['png', 'webp', 'jpg']:  # Added JPG as last resort
            matches = [f for f in os.listdir(folder_path) 
                      if f.lower().startswith(f"{base_name}_001") and f.lower().endswith(f".{ext}")]
            if matches:
                return matches[0]
        return None

    # Process Boxart
    if should_process_asset('GC'):
        boxart_asset = AuroraAssetFile(verbose=verbose)
        boxart_file = find_asset_file('boxart')
        if boxart_file:
            if boxart_asset.import_image(os.path.join(folder_path, boxart_file), AssetType.Boxart, verbose=verbose):
                output_path = os.path.join(output_folder, f"GC{titleid}.asset")
                if boxart_asset.save_asset(output_path, verbose=verbose):
                    if verbose:
                        print(f"Created boxart asset: {output_path}")
                    else:
                        print(f"Created boxart asset: {os.path.basename(output_path)}")
                    assets_created = True


    # Process Background
    if should_process_asset('BK'):
        background_asset = AuroraAssetFile(verbose=verbose)
        background_file = find_asset_file('background')
        if background_file:
            if background_asset.import_image(os.path.join(folder_path, background_file), AssetType.Background, verbose=verbose):
                output_path = os.path.join(output_folder, f"BK{titleid}.asset")
                if background_asset.save_asset(output_path, verbose=verbose):
                    if verbose:
                        print(f"Created background asset: {output_path}")
                    else:
                        print(f"Created background asset: {os.path.basename(output_path)}")
                    assets_created = True


    # Process Banner and Icon together
    if should_process_asset('GL'):
        gl_asset = AuroraAssetFile(verbose=verbose)
        banner_file = find_asset_file('banner')
        icon_file = find_asset_file('icon')
        
        if banner_file and icon_file:
            # Import banner
            if not gl_asset.import_image(os.path.join(folder_path, banner_file), AssetType.Banner, verbose=verbose):
                print("Failed to import banner image")
            # Import icon
            elif not gl_asset.import_image(os.path.join(folder_path, icon_file), AssetType.Icon, verbose=verbose):
                print("Failed to import icon image")
            else:
                output_path = os.path.join(output_folder, f"GL{titleid}.asset")
                if gl_asset.save_asset(output_path, verbose=verbose):
                    if verbose:
                        print(f"Created banner/icon asset: {output_path}")
                    else:
                        print(f"Created banner/icon asset: {os.path.basename(output_path)}")
                    assets_created = True
        else:

            if verbose:
                if not banner_file:
                    print("No banner image found")
                if not icon_file:
                    print("No icon image found")

    # Process Screenshots
    if should_process_asset('SS'):
        screenshot_asset = AuroraAssetFile(verbose=verbose)
        screenshot_files = sorted([f for f in os.listdir(folder_path) if f.lower().startswith('screenshot')])
        if screenshot_files:
            for idx, filename in enumerate(screenshot_files):
                try:
                    asset_type = AssetType(AssetType.Screenshot1 + idx)
                    if not screenshot_asset.import_image(os.path.join(folder_path, filename), asset_type, verbose=verbose):
                        print(f"Failed to import screenshot {idx + 1}")
                        break
                except ValueError:
                    print(f"Warning: Too many screenshots, skipping {filename}")
                    break
            else:
                output_path = os.path.join(output_folder, f"SS{titleid}.asset")
                if screenshot_asset.save_asset(output_path, verbose=verbose):
                    if verbose:
                        print(f"Created screenshots asset with {len(screenshot_files)} screenshots: {output_path}")
                    else:
                        print(f"Created screenshots asset with {len(screenshot_files)} screenshots: {os.path.basename(output_path)}")
                    assets_created = True


    if not assets_created:
        print("No valid assets found in folder or all assets already exist.")


def handle_extract(args):
    extract_asset(args.asset, args.format, verbose=args.verbose)

def extract_asset(asset_path: str, output_format: str = "png", verbose: bool = False):
    # Validate output format
    if output_format.lower() not in ["png", "webp"]:
        print(f"Error: Unsupported output format '{output_format}'. Use png or webp.")
        return

    # Extract TitleID from filename
    base_name = os.path.basename(asset_path)
    if len(base_name) < 12 or not base_name.endswith('.asset'):
        print("Error: Invalid asset filename. Expected format: [BK|GC|GL|SS]<TitleID>.asset")
        return

    prefix = base_name[:2]
    titleid = base_name[2:-6]  # Remove prefix and .asset extension
    output_folder = os.path.join("output", titleid)
    os.makedirs(output_folder, exist_ok=True)

    asset = AuroraAssetFile(verbose=verbose)

    if prefix == "BK":
        # Extract background
        img = asset.extract_image(asset_path, AssetType.Background)
        if img:
            output_path = os.path.join(output_folder, f"background.{output_format}")
            img.save(output_path)
            print(f"Extracted background to {output_path}")
        else:
            print("Failed to extract background")

    elif prefix == "GC":
        # Extract boxart
        img = asset.extract_image(asset_path, AssetType.Boxart)
        if img:
            output_path = os.path.join(output_folder, f"boxart.{output_format}")
            img.save(output_path)
            print(f"Extracted boxart to {output_path}")
        else:
            print("Failed to extract boxart")

    elif prefix == "GL":
        # Extract banner and icon
        banner = asset.extract_image(asset_path, AssetType.Banner)
        if banner:
            output_path = os.path.join(output_folder, f"banner.{output_format}")
            banner.save(output_path)
            print(f"Extracted banner to {output_path}")
        else:
            print("Failed to extract banner")

        icon = asset.extract_image(asset_path, AssetType.Icon)
        if icon:
            output_path = os.path.join(output_folder, f"icon.{output_format}")
            icon.save(output_path)
            print(f"Extracted icon to {output_path}")
        else:
            print("Failed to extract icon")

    elif prefix == "SS":
        # Extract screenshots
        for i in range(AssetType.ScreenshotStart, AssetType.ScreenshotEnd + 1):
            img = asset.extract_image(asset_path, AssetType(i))
            if img:
                output_path = os.path.join(output_folder, f"screenshot{i - AssetType.ScreenshotStart + 1}.{output_format}")
                img.save(output_path)
                print(f"Extracted screenshot {i - AssetType.ScreenshotStart + 1} to {output_path}")
            else:
                break  # Stop when we hit the first missing screenshot
    else:
        print(f"Error: Unknown asset prefix '{prefix}'. Expected BK, GC, GL, or SS.")

def create_texture_header(width: int, height: int, format_code: int = 0x31545844) -> bytes:
    """Create a 52-byte texture header with proper format"""
    header = bytearray(52)
    
    # Format from working files
    header[0:4] = struct.pack('<I', 0x03)  # Format version
    header[4:8] = struct.pack('<I', 0x01)  # Unknown constant
    header[8:12] = struct.pack('<I', 0)    # Reserved
    header[12:16] = struct.pack('<I', 0)   # Reserved
    header[16:20] = struct.pack('<I', 0)   # Reserved
    header[20:24] = b'\xff\xff\x00\x00'    # Width mask
    header[24:28] = b'\xff\xff\x00\x00'    # Height mask
    header[28:32] = struct.pack('<I', format_code)  # DXT format
    header[32:36] = struct.pack('<I', 0x54)  # Constant
    header[36:40] = struct.pack('<I', 0)    # Reserved
    header[40:44] = struct.pack('<I', 0x100d)  # Flags
    header[44:48] = struct.pack('<I', 0)    # Reserved
    header[48:52] = struct.pack('<I', 0x0a)  # Constant

    return header

def write_entry(file, entry_data, width, height, extended_info=0x00030001):
    # Write entry header
    file.write(struct.pack('<I', 0x120))  # Offset to texture data
    file.write(struct.pack('<H', width))  # Width
    file.write(struct.pack('<H', height))  # Height
    file.write(struct.pack('>I', extended_info))  # Extended info (big-endian)
    # Padding to 64 bytes
    file.write(b'\x00' * (64 - 12))

def write_asset_file(output_path, entries):
    with open(output_path, 'wb') as f:
        # Write 256 byte header
        f.write(b'\x00' * 256)
        
        # Write entries (25 entries * 64 bytes = 1600 bytes)
        for entry in entries:
            write_entry(f, *entry)
        
        # Pad to 2048 bytes
        f.write(b'\x00' * (2048 - 256 - 1600))
        
        # Write texture data
        for entry in entries:
            dds_header = create_texture_header(entry[1], entry[2], entry[3])  # entry[3] indicates alpha
            f.write(dds_header)
            f.write(entry[4])  # Texture data

def validate_texture_dimensions(width, height):
    if width < 64 or height < 64:
        raise ValueError(f"Invalid texture dimensions {width}x{height}")
    if width & (width - 1) != 0 or height & (height - 1) != 0:
        raise ValueError(f"Texture dimensions must be power of two: {width}x{height}")

def main():
    parser = argparse.ArgumentParser(
        description='Aurora Asset Converter',
        usage='%(prog)s <command> [options]',
        epilog='Examples:\n'
              '  convert.py background background.png 00000001\n'
              '  convert.py extract BK00000001.asset png\n'
              '  convert.py folder ./assets 00000001\n'
              '  convert.py bannericon --banner banner.png --icon icon.png 00000001',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--version', action='version', version='%(prog)s 1.0.2')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    subparsers = parser.add_subparsers(dest='command', required=True)
    
    # Individual command parsers
    create_background_parser(subparsers)
    create_boxart_parser(subparsers)
    create_screenshots_parser(subparsers)
    create_bannericon_parser(subparsers)
    create_folder_parser(subparsers)
    create_extract_parser(subparsers)
    
    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()