from __future__ import annotations

"""Developer-only model fetch helper.

Final users never run this. During packaging, model assets are downloaded once
by the developer/CI and bundled into the installer.

For compatibility validation we intentionally start with the official generic
ONNX model. After quality is validated, Sprint 02b will benchmark a generic
INT8 quantized build to reduce installer size.
"""

from pathlib import Path
from urllib.request import urlretrieve

BASE = "https://huggingface.co/intfloat/multilingual-e5-small/resolve/main/onnx"
FILES = {
    "model.onnx": f"{BASE}/model.onnx?download=true",
    "tokenizer.json": f"{BASE}/tokenizer.json?download=true",
}

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "resources" / "models" / "multilingual-e5-small-onnx"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, url in FILES.items():
        dest = OUT / name
        if dest.exists() and dest.stat().st_size > 1024:
            print(f"skip: {dest}")
            continue
        print(f"download: {name}")
        urlretrieve(url, dest)
        print(f"saved: {dest} ({dest.stat().st_size / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    main()
