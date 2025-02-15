from abc import ABC, abstractmethod
from typing import List
from framework.memory.entry import MemoryEntry
import threading
from queue import Queue

class MemoryPersistence(ABC):
    """持久化层抽象类"""
    @abstractmethod
    def save(self, scope_key: str, entries: List[MemoryEntry]) -> None:
        pass
        
    @abstractmethod
    def load(self, scope_key: str) -> List[MemoryEntry]:
        pass
        
    @abstractmethod
    def flush(self) -> None:
        """确保所有数据都已持久化"""
        pass

class AsyncMemoryPersistence:
    """异步持久化管理器"""
    def __init__(self, persistence: MemoryPersistence):
        self.persistence = persistence
        self.queue = Queue()
        self.running = True
        self.worker = threading.Thread(target=self._worker, daemon=True)
        self.worker.start()
        
    def _worker(self):
        while self.running:
            try:
                scope_key, entries = self.queue.get(timeout=1)
                self.persistence.save(scope_key, entries)
                self.queue.task_done()
                print(f"Saved {scope_key} with {len(entries)} entries")
            except:
                continue
    
    def load(self, scope_key: str) -> List[MemoryEntry]:
        return self.persistence.load(scope_key)
    
    def save(self, scope_key: str, entries: List[MemoryEntry]):
        self.queue.put((scope_key, entries))
        

    def stop(self):
        self.running = False
        self.worker.join()
        self.persistence.flush()