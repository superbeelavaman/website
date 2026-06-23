import os
import json
import shutil

class Database:
    def __init__(self, file):
        self.database = {}
        self.file = file
        self.backup = file + ".bak"
        if not os.path.exists(file):
            open(self.file, "wt").write("{}")

    def read(self):
        try:
            with open(self.file, "rt") as f:
                self.database = json.loads(f.read())
        except (json.JSONDecodeError, OSError):
            print(f"[db] Failed to read {self.file}, attempting fallback to {self.backup}")
            try:
                with open(self.backup, "rt") as f:
                    self.database = json.loads(f.read())
                print(f"[db] Fallback successful, restoring {self.file} from backup")
                shutil.copy2(self.backup, self.file)
            except (json.JSONDecodeError, OSError) as e:
                print(f"[db] Backup read also failed: {e} — starting with empty database")
                self.database = {}

    def write(self):
        if os.path.exists(self.file):
            shutil.copy2(self.file, self.backup)
        with open(self.file, "wt") as f:
            f.write(json.dumps(self.database))

def database(file):
    return Database(file)
