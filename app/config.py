import json
from pathlib import Path

class Config:
    def __init__(self, path: str = 'config.json'):
        self.path = Path(path)
        self.data = self.load()

    def load(self):
        with open(self.path, 'r') as f:
            return json.load(f)

    def get(self, key, default=None):
        return self.data.get(key, default)