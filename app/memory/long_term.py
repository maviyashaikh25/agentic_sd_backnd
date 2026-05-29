import json
from pathlib import Path


MEMORY_FILE = Path("memory_store.json")


class LongTermMemory:

    def __init__(self):

        if not MEMORY_FILE.exists():

            with open(MEMORY_FILE, "w") as f:
                json.dump([], f)

    def save_memory(self, data):

        memories = self.load_memories()

        memories.append(data)

        with open(MEMORY_FILE, "w") as f:
            json.dump(memories, f, indent=2)

    def load_memories(self):

        with open(MEMORY_FILE, "r") as f:
            return json.load(f)