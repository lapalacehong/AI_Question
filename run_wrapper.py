"""Wrapper: run main.py and capture all output to a log file."""
import sys
import traceback

# Redirect stdout and stderr to file
log = open("run_log.txt", "w", encoding="utf-8")

class Tee:
    def __init__(self, *files):
        self.files = files
    def write(self, data):
        for f in self.files:
            f.write(data)
            f.flush()
    def flush(self):
        for f in self.files:
            f.flush()

sys.stdout = Tee(sys.__stdout__, log)
sys.stderr = Tee(sys.__stderr__, log)

try:
    from main import main
    main()
except Exception as e:
    print(f"\n{'='*60}")
    print(f"FATAL ERROR: {type(e).__name__}: {e}")
    traceback.print_exc()
    print(f"{'='*60}")
finally:
    log.close()
