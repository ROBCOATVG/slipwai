#!/usr/bin/env python3
"""Make the app's icons from `assets/brand/slipwai-app-icon.svg`.

The spec hands PyInstaller `assets/brand/slipwai.icns` for the Mac bundle and `assets/brand/slipwai.ico`
for the Windows app. Without them PyInstaller stamps its own Python icon on both, which is what the
disk image showed. It hands `assets/brand/slipwai-splash.png` to the Windows app as the picture shown
while the one file unpacks itself: the same tile, the name, and room under it for a line of words.

All three are committed, so a build needs nothing this script needs; run it on a Mac with
Chrome when the SVG changes: Chrome draws the SVG, `sips` scales it, `iconutil` packs the `.icns`, and
the `.ico` is PNG entries in the header Windows reads.
"""

import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRAND = ROOT / "assets" / "brand"
SOURCE = BRAND / "slipwai-app-icon.svg"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
ICNS_SIZES = [16, 32, 128, 256, 512]
ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]
#: The picture's size in pixels. The spec's `text_pos` puts the words in the room left under the name.
SPLASH = (460, 180)


def shot(work: Path, page: Path, size: tuple[int, int], png: Path, background: str = "00000000") -> Path:
    """Chrome's picture of `page`, `size` pixels."""
    # Not checked: headless Chrome writes the screenshot and then can exit non-zero tearing itself down.
    run = subprocess.run(
        [CHROME, "--headless", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
         f"--user-data-dir={work / 'chrome'}", f"--default-background-color={background}",
         f"--window-size={size[0]},{size[1]}", f"--screenshot={png}", page.as_uri()],
        capture_output=True, text=True,
    )
    if not png.exists():
        raise SystemExit(f"Chrome drew nothing:\n{run.stderr}")
    return png


def splash(work: Path) -> None:
    """The tile, the name beside it, and nothing where the words go. No rounded corners and no shadow past
    the edge: the picture is a window with no frame, and Windows shows it as the rectangle it is."""
    width, height = SPLASH
    page = work / "splash.html"
    page.write_text(
        "<!doctype html><style>html,body{margin:0}"
        f"body{{width:{width}px;height:{height}px;box-sizing:border-box;border:1px solid #cfc8b6;"
        "background:linear-gradient(#fdfcf8,#f3efe4);position:relative;overflow:hidden;"
        "font-family:-apple-system,'Segoe UI',Helvetica,Arial,sans-serif}"
        "img{position:absolute;left:14px;top:18px}"
        "b{position:absolute;left:172px;top:44px;font-size:40px;letter-spacing:-.5px;color:#22313f}"
        f'</style><img src="{SOURCE.as_uri()}" width="144" height="144"><b>slipwai</b>',
        encoding="utf-8",
    )
    shot(work, page, SPLASH, BRAND / "slipwai-splash.png", "fdfcf8ff")


def draw(work: Path) -> Path:
    page = work / "icon.html"
    page.write_text(
        "<!doctype html><style>html,body{margin:0;background:transparent}img{display:block}</style>"
        f'<img src="{SOURCE.as_uri()}" width="1024" height="1024">',
        encoding="utf-8",
    )
    return shot(work, page, (1024, 1024), work / "icon-1024.png")


def scaled(master: Path, size: int, target: Path) -> Path:
    if size == 1024:
        shutil.copyfile(master, target)
    else:
        subprocess.run(["sips", "-z", str(size), str(size), str(master), "--out", str(target)],
                       check=True, capture_output=True)
    return target


def icns(master: Path, work: Path) -> None:
    iconset = work / "slipwai.iconset"
    iconset.mkdir()
    for size in ICNS_SIZES:
        scaled(master, size, iconset / f"icon_{size}x{size}.png")
        scaled(master, size * 2, iconset / f"icon_{size}x{size}@2x.png")
    subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(BRAND / "slipwai.icns")], check=True)


def ico(master: Path, work: Path) -> None:
    images = [scaled(master, size, work / f"ico-{size}.png").read_bytes() for size in ICO_SIZES]
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = len(header) + 16 * len(images)
    entries, data = b"", b""
    for size, image in zip(ICO_SIZES, images, strict=True):
        # A width or height of 256 is written as 0: the field is one byte.
        side = size % 256
        entries += struct.pack("<BBBBHHII", side, side, 0, 0, 1, 32, len(image), offset + len(data))
        data += image
    (BRAND / "slipwai.ico").write_bytes(header + entries + data)


def main() -> int:
    if sys.platform != "darwin" or not Path(CHROME).exists():
        print("build-icons runs on a Mac with Google Chrome installed.", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory() as directory:
        work = Path(directory)
        master = draw(work)
        icns(master, work)
        ico(master, work)
        splash(work)
    return 0


if __name__ == "__main__":
    sys.exit(main())
