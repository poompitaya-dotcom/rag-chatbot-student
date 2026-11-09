"""Pre-class setup check. Run it from the project folder with your venv active.

At home, before class (downloads ~1.1 GB of model weights, once):
    python setup_check.py

In class (proves everything is already on disk - nothing gets downloaded):
    python setup_check.py --offline
"""
import os
import shutil
import sys
import threading
import time

OFFLINE = "--offline" in sys.argv
if OFFLINE:
    # Must be set before any Hugging Face library is imported.
    os.environ["HF_HUB_OFFLINE"] = "1"

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
GENERATOR_MODEL = "google/flan-t5-base"


def ok(msg):
    print(f"[ok]   {msg}", flush=True)


def warn(msg):
    print(f"[warn] {msg}", flush=True)


def fail(msg, fix):
    print(f"[FAIL] {msg}")
    print(f"       fix: {fix}")
    sys.exit(1)


class Working:
    """Show that a slow step is still running.

    In a terminal it draws a spinner with the elapsed seconds; elsewhere (or
    when spin=False, because a library prints its own progress bars) it
    prints one line saying what's happening.
    """

    FRAMES = "|/-\\"

    def __init__(self, label, spin=True):
        self.label = label
        self.spin = spin and sys.stdout.isatty()
        self._stop = threading.Event()
        self._width = 0

    def __enter__(self):
        self.started = time.monotonic()
        if self.spin:
            self._thread = threading.Thread(target=self._draw, daemon=True)
            self._thread.start()
        else:
            print(f"[....] {self.label}", flush=True)
        return self

    def _draw(self):
        frame = 0
        while not self._stop.wait(0.15):
            line = f"[ {self.FRAMES[frame % 4]}  ] {self.label} ({self.elapsed:.0f}s)"
            self._width = max(self._width, len(line))
            print(f"\r{line}", end="", flush=True)
            frame += 1

    @property
    def elapsed(self):
        return time.monotonic() - self.started

    def __exit__(self, *exc):
        if self.spin:
            self._stop.set()
            self._thread.join()
            print("\r" + " " * self._width + "\r", end="", flush=True)
        return False


# 1. Python version
major, minor = sys.version_info[:2]
if (major, minor) < (3, 10):
    fail(f"Python {major}.{minor} is too old", "install Python 3.11, 3.12 or 3.13 from python.org")
elif (major, minor) > (3, 13):
    warn(f"Python {major}.{minor} hasn't been tested with this project; 3.11-3.13 are known to work")
else:
    ok(f"Python {major}.{minor}")

# 2. Virtual environment (Codespaces installs globally, so it's exempt)
if sys.prefix != sys.base_prefix:
    ok(f"running inside a virtual environment ({sys.prefix})")
elif os.environ.get("CODESPACES"):
    ok("running in Codespaces")
else:
    warn("not inside a virtual environment - activate .venv first (see the guide's Appendix A)")

# 3. git
if shutil.which("git") is None:
    fail("git was not found", "install it from https://git-scm.com, then close and reopen VS Code")
ok("git is installed")

# 4. Python packages. Each import can take a while: the first time, Python
#    compiles thousands of library files. Slowest first.
print("Importing libraries (the first run can take a minute or two)...", flush=True)
versions = {}
for module, name in [
    ("torch", "torch"),
    ("transformers", "transformers"),
    ("sentence_transformers", "sentence-transformers"),
    ("chromadb", "chromadb"),
    ("streamlit", "streamlit"),
]:
    try:
        with Working(f"importing {name}") as step:
            versions[name] = __import__(module).__version__
    except ImportError as e:
        fail(f"missing package: {e.name}", "activate .venv, then run: pip install -r requirements.txt")
    ok(f"{name} {versions[name]} imports ({step.elapsed:.0f}s)")

import torch  # noqa: E402 - already imported above; this just binds the name

# 5. Models actually load (and, with --offline, load without the network).
#    Hugging Face prints its own download and loading progress bars here, so
#    these steps announce themselves instead of spinning.
hint = (
    "run `python setup_check.py` once WITHOUT --offline on a good connection to download the models"
    if OFFLINE
    else "check your internet connection (or proxy) and run this again"
)
download_note = "" if OFFLINE else ", downloads ~90 MB the first time"

try:
    with Working(f"loading {EMBEDDING_MODEL}{download_note}...", spin=False) as step:
        from sentence_transformers import SentenceTransformer

        embedding_model = SentenceTransformer(EMBEDDING_MODEL, device="cpu")
        vector = embedding_model.encode("hello world")
except Exception as e:
    fail(f"could not load {EMBEDDING_MODEL}: {e}", hint)
ok(f"embedding model loads ({EMBEDDING_MODEL}, vector size {len(vector)}, {step.elapsed:.0f}s)")

download_note = "" if OFFLINE else ", downloads ~1 GB the first time"
try:
    with Working(f"loading {GENERATOR_MODEL}{download_note}...", spin=False) as step:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(GENERATOR_MODEL)
        generator = AutoModelForSeq2SeqLM.from_pretrained(GENERATOR_MODEL)
    with Working("asking the generator a test question") as answer_step:
        inputs = tokenizer("Answer briefly. Question: What colour is the sky? Answer:", return_tensors="pt")
        with torch.inference_mode():
            output = generator.generate(**inputs, max_new_tokens=8)
        reply = tokenizer.decode(output[0], skip_special_tokens=True)
except Exception as e:
    fail(f"could not load {GENERATOR_MODEL}: {e}", hint)
ok(f"generator loads and answers ({GENERATOR_MODEL} says: {reply!r}, "
   f"{step.elapsed + answer_step.elapsed:.0f}s)")

print()
print("All checks passed." + (" Models are cached - no downloads needed in class." if OFFLINE else ""))
