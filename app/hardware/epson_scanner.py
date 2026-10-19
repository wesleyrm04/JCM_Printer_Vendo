import os
import win32com.client
import pythoncom
from app.hardware.interfaces import ScannerInterface

class EpsonScanner(ScannerInterface):
    def get_status(self):
        """WIA is difficult to poll silently, assume ready if no COM errors."""
        return {"status": "READY"}

    def scan_document(self, output_path: str) -> bool:
        """Triggers the physical scan and saves it as a JPEG."""
        print("[SCANNER] Initializing WIA hardware scan...")
        try:
            # Must initialize COM for background threads
            pythoncom.CoInitialize()
            
            device_manager = win32com.client.Dispatch("WIA.DeviceManager")
            
            scanner_info = None
            for info in device_manager.DeviceInfos:
                if info.Type == 1: # 1 = Scanner
                    scanner_info = info
                    break
                    
            if not scanner_info:
                print("[SCANNER ERROR] No scanner found.")
                return False

            # Connect directly to bypass the UI dialogs
            device = scanner_info.Connect()
            item = device.Items[1]

            WIA_IMG_FORMAT_JPEG = "{B96B3CAE-0728-11D3-9D7B-0000F81EF32E}"
            image = item.Transfer(WIA_IMG_FORMAT_JPEG)

            if os.path.exists(output_path):
                os.remove(output_path)

            image.SaveFile(output_path)
            print(f"[SCANNER] Scan successful. Saved to {output_path}")
            return True

        except Exception as e:
            print(f"[SCANNER ERROR] {e}")
            return False
            
        finally:
            # Memory cleanup to prevent COM leaks over time
            image = None
            item = None
            device = None
            device_manager = None
            pythoncom.CoUninitialize()