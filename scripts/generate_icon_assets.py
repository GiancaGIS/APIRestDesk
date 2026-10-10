"""Regenerate runtime and desktop icons from the editable SVG using PyQt6.

Run from any directory: python scripts/generate_icon_assets.py
No additional image conversion dependencies are required.
"""

from __future__ import annotations

import os
import struct
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QBuffer, QIODevice, QRectF
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QApplication


ASSETS_DIR = Path(__file__).resolve().parents[1] / "api_rest_desk" / "assets"


def render_png(renderer: QSvgRenderer, size: int) -> bytes:
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(0)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    if not image.save(buffer, "PNG"):
        raise RuntimeError(f"Could not encode the {size}px icon")
    return bytes(buffer.data())


def main() -> None:
    app = QApplication.instance() or QApplication([])
    renderer = QSvgRenderer(str(ASSETS_DIR / "app_icon.svg"))
    if not renderer.isValid():
        raise RuntimeError("Invalid app_icon.svg")
    sizes = (16, 24, 32, 48, 64, 128, 256, 512, 1024)
    pngs = {size: render_png(renderer, size) for size in sizes}
    (ASSETS_DIR / "app_icon.png").write_bytes(pngs[1024])

    # Windows ICO: directory entries plus PNG payloads for each resolution.
    ico_sizes = (16, 24, 32, 48, 64, 128, 256)
    offset = 6 + 16 * len(ico_sizes)
    entries = []
    for size in ico_sizes:
        payload = pngs[size]
        dimension = size if size < 256 else 0
        entries.append(struct.pack("<BBBBHHII", dimension, dimension, 0, 0, 1, 32, len(payload), offset))
        offset += len(payload)
    ico = struct.pack("<HHH", 0, 1, len(ico_sizes)) + b"".join(entries)
    ico += b"".join(pngs[size] for size in ico_sizes)
    (ASSETS_DIR / "app_icon.ico").write_bytes(ico)

    # macOS ICNS: modern PNG-backed elements, including Retina resolutions.
    icns_types = {
        b"icp4": 16, b"icp5": 32, b"icp6": 64, b"ic07": 128, b"ic08": 256,
        b"ic09": 512, b"ic10": 1024, b"ic11": 32, b"ic12": 64, b"ic13": 256, b"ic14": 512,
    }
    chunks = [kind + struct.pack(">I", len(pngs[size]) + 8) + pngs[size] for kind, size in icns_types.items()]
    payload = b"".join(chunks)
    (ASSETS_DIR / "app_icon.icns").write_bytes(b"icns" + struct.pack(">I", len(payload) + 8) + payload)
    print(f"Generated PNG, ICO and ICNS in {ASSETS_DIR}")
    del app


if __name__ == "__main__":
    main()
