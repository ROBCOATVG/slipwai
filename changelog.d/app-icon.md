PATCH

**The app wears the slipwai mark, not PyInstaller's Python icon.** The Mac app in the disk image and the
Windows app now carry the tug on a tile, made from `assets/brand/slipwai-app-icon.svg` into the
`slipwai.icns` and `slipwai.ico` beside it by `scripts/build-icons.py`, and the executable smoke fails a
build whose app does not carry them. The command keeps no icon, as before.

**Catch-up:** nothing; the app's look, and nothing a project carries.
