import os
import shutil
import uuid
from ctypes import windll
from typing import List, Dict
from pypdf import PdfReader

# Allowed file types and max size (50 MB)
ALLOWED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png'}
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024 
TEMP_WORKSPACE = os.path.join(os.getcwd(), "temp_workspace")

# Ensure the temp folder exists when the module loads
os.makedirs(TEMP_WORKSPACE, exist_ok=True)

class USBManager:
    @staticmethod
    def get_usb_drives() -> List[str]:
        """Finds all removable drives in Windows."""
        drives = []
        bitmask = windll.kernel32.GetLogicalDrives()
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            if bitmask & 1:
                drive_path = f"{letter}:\\"
                if windll.kernel32.GetDriveTypeW(drive_path) == 2:
                    drives.append(drive_path)
            bitmask >>= 1
        return drives

    @staticmethod
    def scan_usb_files() -> List[Dict]:
        """Scans all USB drives and returns a sanitized list of printable files."""
        usb_drives = USBManager.get_usb_drives()
        safe_files = []

        for drive in usb_drives:
            for root, dirs, files in os.walk(drive):
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if ext in ALLOWED_EXTENSIONS:
                        full_path = os.path.join(root, file)
                        try:
                            file_size = os.path.getsize(full_path)
                            if file_size <= MAX_FILE_SIZE_BYTES:
                                safe_files.append({
                                    "filename": file,
                                    "path": full_path,
                                    "size_kb": round(file_size / 1024, 2),
                                    "extension": ext
                                })
                        except OSError:
                            pass # Skip files we can't read
        return safe_files

    @staticmethod
    def get_page_count(file_path: str) -> int:
        """Securely reads the file metadata to determine the page count."""
        if not os.path.exists(file_path):
            raise FileNotFoundError("File not found.")
            
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext in {'.jpg', '.jpeg', '.png'}:
            return 1 # Images are always 1 page
            
        if ext == '.pdf':
            try:
                reader = PdfReader(file_path)
                return len(reader.pages)
            except Exception as e:
                print(f"[PDF ERROR] Failed to read page count: {e}")
                return 1 # Fallback in case of a mildly corrupted PDF
                
        return 1

    @staticmethod
    def isolate_file_for_printing(usb_file_path: str) -> str:
        """Copies file from USB to local temp workspace and renames securely."""
        if not os.path.exists(usb_file_path):
            raise FileNotFoundError("File not found on USB. Was it removed?")
            
        ext = os.path.splitext(usb_file_path)[1].lower()
        safe_filename = f"job_{uuid.uuid4().hex}{ext}"
        local_path = os.path.join(TEMP_WORKSPACE, safe_filename)
        
        shutil.copy2(usb_file_path, local_path)
        return local_path

    @staticmethod
    def cleanup_workspace():
        """Deletes all files in the temp workspace."""
        for file in os.listdir(TEMP_WORKSPACE):
            file_path = os.path.join(TEMP_WORKSPACE, file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(f"[CLEANUP ERROR] Failed to delete {file_path}: {e}")