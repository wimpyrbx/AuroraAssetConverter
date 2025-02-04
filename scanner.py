import struct
import os
from pathlib import Path
from enum import IntEnum
import argparse
from datetime import datetime
from colorama import init, Fore, Style # type: ignore
import logging
from typing import Dict, List, Tuple, Optional

init()

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
    ScreenshotStart = 5
    ScreenshotEnd = 9
    Max = 24

class AssetScanner:
    MAGIC = 0x52584541
    HEADER_SIZE, ENTRY_SIZE, ALIGNMENT = 20, 64, 2048
    SIZE_TOLERANCE = 0.01
    SIZE_THRESHOLDS = {
        'BK': 983040, 'GC': 655360, 
        'GL': 83968, 'SS': 3276800
    }
    EXPECTED_ENTRIES = {'BK': 1, 'GC': 1, 'GL': 2, 'SS': 5}
    ASSET_PATTERNS = {
        b'\x00\x59\xe4\xff': 'Background',
        b'\x00\x4a\xe3\x83': 'Boxart',
        b'\x00\x07\xe0\x3f': 'Icon',
        b'\x00\x0b\xe1\xa3': 'Banner',
        b'\x00\x46\x23\xe7': 'Screenshot'
    }
    EXPECTED_TYPES = {
        ('GL', 0): 'Icon', ('GL', 1): 'Banner',
        ('GC', 2): 'Boxart', ('BK', 4): 'Background'
    }

    def __init__(self, verbose=False, very_verbose=False):
        self.verbose, self.vv = verbose, very_verbose
        logging.basicConfig(filename='scanner.log', filemode='w',
                          format='%(asctime)s - %(levelname)s - %(message)s',
                          level=logging.DEBUG)

    def _swap32(self, val: int) -> int: return struct.unpack(">I", struct.pack("<I", val))[0]

    def _log(self, msg: str, status: Optional[str]=None, folder: str=None):
        logging.error(msg) if status == 'FAIL' else logging.info(msg)
        if not self.verbose: return

        timestamp = datetime.now().strftime('%H:%M:%S')
        colors = {'OK': Fore.GREEN, 'FAIL': Fore.RED}
        parts = [
            f"[{timestamp}]",
            f"{colors[status]}[{status}]{Style.RESET_ALL}" if status else '',
            msg.replace(f'[{status}]', '').strip()
        ]
        print(' '.join(filter(None, parts)))

    def _validate_metadata(self, prefix: str, idx: int, meta: bytes) -> bool:
        if self.vv: print(f"  Checking {prefix}{idx}: {' '.join(f'{b:02x}' for b in meta)}")
        expected = self.EXPECTED_TYPES.get((prefix, idx), 
                  'Screenshot' if prefix == 'SS' and 5 <= idx <= 9 else None)
        return self.ASSET_PATTERNS.get(meta, '') == expected

    def _validate_size(self, size: int, prefix: str) -> bool:
        target = self.SIZE_THRESHOLDS[('GL' if prefix == 'GL' else prefix)]
        return target * (1 - self.SIZE_TOLERANCE) <= size <= target * (1 + self.SIZE_TOLERANCE)

    def scan_asset(self, path: Path) -> Tuple[bool, List[str]]:
        issues = []
        try:
            with path.open('rb') as f:
                if self._swap32(struct.unpack('<I', f.read(4))[0]) != self.MAGIC:
                    return False, ["Invalid magic"]
                
                f.seek(12)
                flags, ss_count = map(self._swap32, struct.unpack('<II', f.read(8)))
                prefix = path.name[:2]
                entry_count = 0

                for idx in range(AssetType.Max + 1):
                    entry = f.read(self.ENTRY_SIZE)
                    if len(entry) < self.ENTRY_SIZE: break
                    size = self._swap32(struct.unpack('<I', entry[4:8])[0])
                    
                    if size > 0:
                        entry_count += 1
                        meta = entry[48:52]
                        if not self._validate_metadata(prefix, idx, meta):
                            issues.append(f"Invalid metadata at {idx}: {meta.hex()}")
                
                if entry_count != self.EXPECTED_ENTRIES[prefix]:
                    issues.append(f"Expected {self.EXPECTED_ENTRIES[prefix]} entries, found {entry_count}")
                
                if not self._validate_size(path.stat().st_size, prefix):
                    issues.append(f"Size mismatch for {prefix}")
                
        except Exception as e: issues.append(f"Read error: {str(e)}")
        return len(issues) == 0, issues

    def scan_folder(self, path: Path) -> bool:
        self._log(f"Scanning {path.name}", folder=path.name)
        print(f"{'-'*75}")
        assets = list(path.rglob("*.asset"))
        if len(assets) != 4: 
            self._log(f"Invalid asset count: found {len(assets)}, expected 4", 'FAIL', path.name)
            return False

        basenames = {a.name[2:] for a in assets}
        if len(basenames) > 1:
            self._log(f"Name mismatch: {', '.join(basenames)}", 'FAIL', path.name)
            return False

        valid = True
        for asset in assets:
            ok, issues = self.scan_asset(asset)
            status = 'OK' if ok else 'FAIL'
            self._log(f"{asset.name}: {status}", status, path.name)
            valid &= ok
            for issue in issues: self._log(issue, 'FAIL', path.name)
        
        print("")
        return valid

    def scan_root(self, root: Path):

        if not root.exists(): return self._log("Invalid path", 'FAIL')
        
        folders = [f for f in root.iterdir() if f.is_dir()]
        total = len(folders)
        valid = sum(self.scan_folder(f) for f in folders)

        print(f"{'-'*75}\nCompleted scan: {Style.BRIGHT}{valid}/{total} valid.\n")



def main():
    parser = argparse.ArgumentParser(description='Aurora Asset Scanner')
    parser.add_argument('path', help='Root path to scan')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('-vv', '--very-verbose', action='store_true', help='Debug output')
    args = parser.parse_args()
    
    AssetScanner(args.verbose, args.very_verbose).scan_root(Path(args.path))

if __name__ == "__main__":
    main()