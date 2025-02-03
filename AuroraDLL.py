import ctypes
from ctypes import c_int, c_void_p, byref, create_string_buffer, addressof
import sys

class AuroraDLL:
    def __init__(self, dll_path=".\AuroraAsset.dll", verbose=False):
        self.verbose = verbose
        try:
            if sys.platform.startswith("win"):
                self.dll = ctypes.CDLL(dll_path)
            else:
                raise OSError("This DLL implementation only works on Windows")
            
            self._setup_functions()
            if self.verbose:
                print(f"Successfully loaded DLL from: {dll_path}")
        except Exception as e:
            print(f"Failed to load DLL: {e}")
            raise

    def _setup_functions(self):
        # ConvertImageToAsset
        self.dll.ConvertImageToAsset.argtypes = [
            ctypes.POINTER(ctypes.c_ubyte),  # imageData
            ctypes.c_int,                    # imageDataLen
            ctypes.c_int,                    # imageWidth
            ctypes.c_int,                    # imageHeight
            ctypes.c_int,                    # useCompression
            ctypes.POINTER(ctypes.c_ubyte),  # headerData
            ctypes.POINTER(ctypes.c_int),    # headerDataLen
            ctypes.POINTER(ctypes.c_ubyte),  # videoData
            ctypes.POINTER(ctypes.c_int)      # videoDataLen
        ]
        self.dll.ConvertImageToAsset.restype = ctypes.c_int

        # ConvertAssetToImage
        self.dll.ConvertAssetToImage.argtypes = [
            ctypes.POINTER(ctypes.c_ubyte),  # headerData
            ctypes.c_int,                    # headerDataLen
            ctypes.POINTER(ctypes.c_ubyte),  # videoData
            ctypes.c_int,                    # videoDataLen
            ctypes.POINTER(ctypes.c_ubyte),  # imageData
            ctypes.POINTER(ctypes.c_int),    # imageDataLen
            ctypes.POINTER(ctypes.c_int),    # imageWidth
            ctypes.POINTER(ctypes.c_int)     # imageHeight
        ]
        self.dll.ConvertAssetToImage.restype = ctypes.c_int

        # ConvertDDSToImage
        self.dll.ConvertDDSToImage.argtypes = [
            c_void_p, c_int, c_void_p, ctypes.POINTER(c_int),
            ctypes.POINTER(c_int), ctypes.POINTER(c_int)
        ]
        self.dll.ConvertDDSToImage.restype = c_int

    def _check_dll_loaded(self):
        if not self.dll:
            raise RuntimeError("DLL not properly initialized")

    def process_image_to_asset(self, image_data, width, height, compression):
        if self.verbose:
            print("  Processing image to asset...")
        try:
            # Convert Python bytes to ctypes array
            image_data_ptr = (ctypes.c_ubyte * len(image_data)).from_buffer_copy(image_data)
            
            # Prepare output buffers
            header_data_len = ctypes.c_int()
            video_data_len = ctypes.c_int()
            
            # First call to get buffer sizes
            result = self.dll.ConvertImageToAsset(
                image_data_ptr, len(image_data), width, height, int(compression),
                None, ctypes.byref(header_data_len), None, ctypes.byref(video_data_len)
            )
            
            if result == 1:
                # Allocate buffers
                header_data = (ctypes.c_ubyte * header_data_len.value)()
                video_data = (ctypes.c_ubyte * video_data_len.value)()
                
                # Second call to get actual data
                result = self.dll.ConvertImageToAsset(
                    image_data_ptr, len(image_data), width, height, int(compression),
                    header_data, ctypes.byref(header_data_len),
                    video_data, ctypes.byref(video_data_len)
                )
                
                if result == 1:
                    if self.verbose:
                        print("  Image processing successful")
                    return True, bytes(header_data), bytes(video_data)
        except Exception as e:
            print(f"Error in process_image_to_asset: {e}")
        return False, None, None

    def process_asset_to_image(self, texture_header, video_data):
        try:
            # Convert texture_header and video_data to ctypes arrays
            texture_header = (ctypes.c_ubyte * len(texture_header))(*texture_header)
            video_data = (ctypes.c_ubyte * len(video_data))(*video_data)
            
            # Prepare output buffers
            image_data = (ctypes.c_ubyte * (1024 * 1024 * 4))()  # Max 1MB image buffer
            image_data_len = ctypes.c_int()
            width = ctypes.c_int()
            height = ctypes.c_int()
            
            # Call the DLL function
            result = self.dll.ConvertAssetToImage(
                texture_header, len(texture_header),
                video_data, len(video_data),
                image_data, ctypes.byref(image_data_len),
                ctypes.byref(width), ctypes.byref(height)
            )
            
            if result == 1:
                return True, bytes(image_data[:image_data_len.value]), width.value, height.value
            return False, None, 0, 0
        except Exception as e:
            print(f"Error in process_asset_to_image: {e}")
            return False, None, 0, 0

    def process_dds_to_image(self, dds_data):
        try:
            dds_len = len(dds_data)
            if dds_len == 0:
                return False, None, 0, 0

            # Create DDS buffer
            dds_buffer = create_string_buffer(dds_data)

            # First call to get image size
            image_len = c_int()
            width = c_int()
            height = c_int()
            result = self.dll.ConvertDDSToImage(
                addressof(dds_buffer), dds_len,
                None, byref(image_len),
                byref(width), byref(height)
            )
            if result != 1:
                return False, None, 0, 0

            # Create output buffer
            image_buffer = create_string_buffer(image_len.value)

            # Second call to get actual data
            result = self.dll.ConvertDDSToImage(
                addressof(dds_buffer), dds_len,
                addressof(image_buffer), byref(image_len),
                byref(width), byref(height)
            )
            if result != 1:
                return False, None, 0, 0

            return True, image_buffer.raw, width.value, height.value

        except Exception as e:
            print(f"Error in process_dds_to_image: {str(e)}")
            return False, None, 0, 0

# Example usage
if __name__ == "__main__":
    converter = AuroraDLL()

    # Convert image to asset
    with open("input_image.bin", "rb") as f:
        pixel_data = f.read()
    success, header, video = converter.process_image_to_asset(
        pixel_data, 512, 512, True
    )
    if success:
        with open("output.asset", "wb") as f:
            f.write(header + video)  # Adjust based on actual .asset format

    # Convert asset to image
    with open("input.asset", "rb") as f:
        asset_data = f.read()
    # Assuming header is first 128 bytes (adjust based on actual format)
    header_data = asset_data[:128]
    video_data = asset_data[128:]
    success, image_data, width, height = converter.process_asset_to_image(
        header_data, video_data
    )
    if success:
        with open("output.bin", "wb") as f:
            f.write(image_data)

    # Convert DDS to image
    with open("input.dds", "rb") as f:
        dds_data = f.read()
    success, image_data, width, height = converter.process_dds_to_image(dds_data)
    if success:
        with open("output_from_dds.bin", "wb") as f:
            f.write(image_data)