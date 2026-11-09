"""The LumaBox support bot.

Once both models are in the local Hugging Face cache (setup_check.py puts
them there), switch the hub to offline mode before any library loads it.
Otherwise every run asks the hub whether the models changed, which is slow
on classroom Wi-Fi and hangs when the network is down.
"""
import os
from pathlib import Path

_MODELS = ["sentence-transformers/all-MiniLM-L6-v2", "google/flan-t5-base"]


def _hub_cache():
    if os.environ.get("HF_HUB_CACHE"):
        return Path(os.environ["HF_HUB_CACHE"])
    hf_home = os.environ.get("HF_HOME") or Path.home() / ".cache" / "huggingface"
    return Path(hf_home) / "hub"


def _models_cached():
    hub = _hub_cache()
    return all(
        any((hub / ("models--" + name.replace("/", "--")) / "snapshots").glob("*/config.json"))
        for name in _MODELS
    )


if _models_cached():
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
