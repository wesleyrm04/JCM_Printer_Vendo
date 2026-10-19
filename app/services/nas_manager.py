import os
import shutil
import uuid
from typing import List, Dict

# Your live NAS storage path
NAS_DIRECTORY = r"\\192.168.8.2\nas\jess\customer_orders"

ALLOWED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png'}
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024 
TEMP_WORKSPACE = os.path.join(os.getcwd(), "temp_workspace")

# Ensure the local temp folder exists
os.makedirs(TEMP_WORKSPACE, exist_ok=True)

class NASManager:
    @staticmethod
    def search_files(search_query: str = "") -> List[Dict]:
        """Scans the NAS directory and filters by the search query (customer name)."""
        safe_files = []
        
        # Check if the NAS is actually connected and reachable
        if not os.path.exists(NAS_DIRECTORY):
            print(f"[NAS ERROR] Directory not found or network disconnected: {NAS_DIRECTORY}")
            return safe_files

        search_query = search_query.lower()

        for root, dirs, files in os.walk(NAS_DIRECTORY):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                
                # If they typed a search, check if the folder name or file name matches
                folder_name = os.path.basename(root).lower()
                file_name_lower = file.lower()
                
                if search_query and search_query not in folder_name and search_query not in file_name_lower:
                    continue

                if ext in ALLOWED_EXTENSIONS:
                    full_path = os.path.join(root, file)
                    try:
                        file_size = os.path.getsize(full_path)
                        if file_size <= MAX_FILE_SIZE_BYTES:
                            # Show the parent folder name (which is usually the customer's name) + file
                            display_name = f"{os.path.basename(root)} / {file}" if root != NAS_DIRECTORY else file
                            
                            safe_files.append({
                                "filename": display_name,
                                "path": full_path,
                                "size_kb": round(file_size / 1024, 2),
                                "extension": ext
                            })
                    except OSError:
                        pass
        return safe_files

    @staticmethod
    def isolate_file_for_printing(nas_file_path: str) -> str:
        """Copies file from NAS to local temp workspace and renames securely."""
        if not os.path.exists(nas_file_path):
            raise FileNotFoundError("File not found on NAS. Was it deleted?")
            
        ext = os.path.splitext(nas_file_path)[1].lower()
        safe_filename = f"job_{uuid.uuid4().hex}{ext}"
        local_path = os.path.join(TEMP_WORKSPACE, safe_filename)
        
        shutil.copy2(nas_file_path, local_path)
        return local_path