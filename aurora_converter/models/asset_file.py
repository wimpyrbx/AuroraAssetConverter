from PIL import Image
import struct
from typing import Optional
from aurora_converter.utils.exceptions import AssetError, AssetFileError

class AuroraAssetFile:
    def __init__(self, dll_path=".\AuroraAsset.dll", verbose=False):
        self.verbose = verbose
        try:
            self.converter = AuroraDLL(dll_path, verbose=self.verbose)
            if self.verbose:
                print("AuroraAssetFile initialized successfully")
        except Exception as e:
            print(f"Failed to initialize converter: {e}")
            print("\nPlease ensure:")
            print("1. The AuroraAsset.dll file is in the same directory as the script")
            print("2. You're using the correct version (32/64-bit) of the DLL for your Python installation")
            print("3. The DLL is accessible and not blocked by your system")
            raise
        self.flags = 0
        self.screenshot_count = 0
        self.MAGIC = 0x52584541  # 'AXER' in ASCII
        self.VERSION = 1
        self.ALIGNMENT = 2048
        self.HEADER_SIZE = 20
        self.ENTRY_SIZE = 64
        self.entries = [{'offset': 0, 'size': 0, 'texture_header': bytearray(52), 'video_data': bytearray()} 
                       for _ in range(AssetType.Max + 1)]

    def import_image(self, image_path: str, asset_type: AssetType = AssetType.Background, compression: bool = True, verbose: bool = False) -> bool:
        try:
            if verbose:
                print(f"\nImporting {asset_type.name} from: {image_path}")
            with Image.open(image_path) as img:
                if verbose:
                    print(f"  Image size: {img.width}x{img.height}")
                img = img.convert('RGBA')
                raw_bytes = bytearray()
                for y in range(img.height):
                    for x in range(img.width):
                        r, g, b, a = img.getpixel((x, y))
                        raw_bytes.extend([a, r, g, b])

            if verbose:
                print("  Converting image to asset format...")
            success, header, video = self.converter.process_image_to_asset(
                bytes(raw_bytes), img.width, img.height, compression
            )
            
            if success:
                if verbose:
                    print("  Conversion successful")
                # Clear existing flags
                self.flags = 0
                
                # Set entry index and flags based on asset type
                if asset_type == AssetType.Boxart:
                    entry_idx = 2
                    self.flags = 0x04  # Boxart flag
                    if verbose:
                        print("  Asset type: Boxart (Entry 2, Flag 0x04)")
                elif asset_type == AssetType.Background:
                    entry_idx = 4
                    self.flags = 0x10  # Background flag
                    if verbose:
                        print("  Asset type: Background (Entry 4, Flag 0x10)")
                elif asset_type in [AssetType.Icon, AssetType.Banner]:
                    entry_idx = 0 if asset_type == AssetType.Icon else 1
                    self.flags = 0x01  # Icon/Banner flag
                    if verbose:
                        print(f"  Asset type: {'Icon' if asset_type == AssetType.Icon else 'Banner'} "
                             f"(Entry {entry_idx}, Flag 0x01)")
                elif AssetType.ScreenshotStart <= asset_type <= AssetType.ScreenshotEnd:
                    entry_idx = asset_type.value
                    self.flags = (1 << asset_type.value)
                    self.screenshot_count = max(self.screenshot_count, 
                                               asset_type.value - AssetType.ScreenshotStart + 1)
                    if verbose:
                        print(f"  Asset type: Screenshot {asset_type.value - AssetType.ScreenshotStart + 1} "
                             f"(Entry {entry_idx}, Flag {hex(self.flags)})")

                # Clear the target entry before writing new data
                self.entries[entry_idx] = {
                    'offset': 0,
                    'size': len(video),
                    'texture_header': bytearray(header),
                    'video_data': bytearray(video)
                }
                if verbose:
                    print(f"  Stored data in entry {entry_idx} (Size: {len(video)} bytes)")
                
            return success
        except Exception as e:
            print(f"Error importing image: {e}")
            return False

    def save_asset(self, output_path: str, verbose: bool = False) -> bool:
        try:
            if verbose:
                print(f"\nSaving asset to: {output_path}")
                print(f"  Magic: {hex(self.MAGIC)} ('AXER')")
                print(f"  Version: {self.VERSION}")
                print(f"  Flags: {hex(self.flags)}")
                print(f"  Screenshot Count: {self.screenshot_count}")
            
            with open(output_path, 'wb') as f:
                # Write header
                f.write(struct.pack('<I', self._swap_uint32(self.MAGIC)))  # Magic
                f.write(struct.pack('<I', self._swap_uint32(self.VERSION)))  # Version
                f.write(struct.pack('<I', self._swap_uint32(0)))  # DataSize (will be updated later)
                f.write(struct.pack('<I', self._swap_uint32(self.flags)))  # Flags
                f.write(struct.pack('<I', self._swap_uint32(self.screenshot_count)))  # ScreenshotCount

            if verbose:
                print("\nWriting entry table:")
            # Write entry table
            for idx, entry in enumerate(self.entries):
                if entry['size'] > 0 and verbose:
                    print(f"  Entry {idx}: Size={entry['size']} bytes")
                f.write(struct.pack('<I', self._swap_uint32(entry['offset'])))  # Offset
                f.write(struct.pack('<I', self._swap_uint32(entry['size'])))  # Size
                f.write(struct.pack('<I', self._swap_uint32(0)))  # ExtendedInfo
                f.write(entry['texture_header'])  # TextureHeader (52 bytes)

            # Calculate data size and update header
            data_size = sum(len(entry['video_data']) for entry in self.entries)
            f.seek(8)  # Go back to DataSize position
            f.write(struct.pack('<I', self._swap_uint32(data_size)))
            if verbose:
                print(f"\nTotal data size: {data_size} bytes")

            # Write padding to align to 2048 bytes
            current_pos = f.tell()
            padding_size = (self.ALIGNMENT - (current_pos % self.ALIGNMENT)) % self.ALIGNMENT
            if verbose and padding_size > 0:
                print(f"  Adding {padding_size} bytes padding for alignment")
            f.write(bytearray(padding_size))

            if verbose:
                print("\nWriting video data:")
            # Write video data
            for idx, entry in enumerate(self.entries):
                if entry['video_data'] and verbose:
                    print(f"  Writing {len(entry['video_data'])} bytes for entry {idx}")
                if entry['video_data']:
                    f.write(entry['video_data'])

            if verbose:
                print("\nAsset saved successfully!")
            return True
        except Exception as e:
            print(f"Error saving asset: {e}")
            return False

    def extract_image(self, asset_path: str, asset_type: AssetType) -> Optional[Image.Image]:
        try:
            with open(asset_path, 'rb') as f:
                data = f.read()

            if len(data) < self.ALIGNMENT:
                raise AssetFileError("Invalid asset file size")

            # Validate header
            magic = self._swap_uint32(struct.unpack('<I', data[0:4])[0])
            version = self._swap_uint32(struct.unpack('<I', data[4:8])[0])
            
            if magic != self.MAGIC:
                raise AssetFileError("Invalid asset file magic")
            if version != self.VERSION:
                raise AssetFileError("Unsupported asset file version")

            # Read entry table
            entry_offset = self.HEADER_SIZE + (asset_type.value * self.ENTRY_SIZE)
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
                img_array = bytearray(image_data)
                for i in range(0, len(img_array), 4):
                    img_array[i], img_array[i+1], img_array[i+2], img_array[i+3] = \
                        img_array[i+3], img_array[i+2], img_array[i+1], img_array[i]
                
                return Image.frombytes('RGBA', (width, height), bytes(img_array))
            return None
        except Exception as e:
            raise AssetError(f"Error extracting image: {e}") from e

    def _swap_uint32(self, value: int) -> int:
        return struct.unpack(">I", struct.pack("<I", value))[0]

    def _calculate_data_offset(self) -> int:
        offset = self.HEADER_SIZE + (len(self.entries) * self.ENTRY_SIZE)
        return offset + (self.ALIGNMENT - (offset % self.ALIGNMENT)) 