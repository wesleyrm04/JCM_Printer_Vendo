import os
import subprocess
import win32print
from app.hardware.interfaces import PrinterInterface

class EpsonPrinter(PrinterInterface):
    def __init__(self, printer_name="EPSON L360 Series"):
        self.printer_name = printer_name
        self.sumatra_path = r"C:\Program Files\SumatraPDF\SumatraPDF.exe"

    def get_status(self) -> dict:
        try:
            hprinter = win32print.OpenPrinter(self.printer_name)
            jobs = win32print.EnumJobs(hprinter, 0, -1, 2)
            win32print.ClosePrinter(hprinter)
            is_active = len(jobs) > 0
            return {"status": "PRINTING" if is_active else "IDLE", "jobs_in_queue": len(jobs)}
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}

    def print_document(self, file_path: str, copies: int = 1, color_mode: str = "BW", page_range: str = "") -> bool:
        if not os.path.exists(self.sumatra_path):
            print(f"[PRINTER] CRITICAL: SumatraPDF not found at {self.sumatra_path}")
            return False

        if not os.path.exists(file_path):
            print(f"[PRINTER] CRITICAL: File not found {file_path}")
            return False

        print(f"[PRINTER] Spooling {file_path} to {self.printer_name} | Copies: {copies} | Range: {page_range}")
        
        # Build SumatraPDF settings string (e.g., "3x, 1-5")
        settings = []
        if copies > 1:
            settings.append(f"{copies}x")
        if page_range.strip():
            settings.append(page_range.strip())
            
        settings_str = ",".join(settings)

        command = [
            self.sumatra_path,
            "-silent",
            "-print-to", self.printer_name
        ]
        
        if settings_str:
            command.extend(["-print-settings", settings_str])
            
        command.append(file_path)

        try:
            subprocess.Popen(command)
            return True
        except Exception as e:
            print(f"[PRINTER] Failed to execute print command: {e}")
            return False