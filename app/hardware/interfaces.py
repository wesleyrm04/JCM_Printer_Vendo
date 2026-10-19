from abc import ABC, abstractmethod
from typing import Dict, Callable

class PrinterInterface(ABC):
    @abstractmethod
    def get_status(self) -> Dict[str, str]:
        pass

    @abstractmethod
    def print_document(self, file_path: str, copies: int, color_mode: str, page_range: str = "") -> bool:
        pass

class ScannerInterface(ABC):
    @abstractmethod
    def get_status(self) -> Dict[str, str]:
        pass

    @abstractmethod
    def scan_document(self, output_path: str) -> bool:
        pass

class PaymentInterface(ABC):
    @abstractmethod
    def connect(self) -> bool:
        pass

    @abstractmethod
    def start_listening(self, on_coin_inserted: Callable[[float], None]):
        pass
        
    @abstractmethod
    def stop_listening(self):
        pass