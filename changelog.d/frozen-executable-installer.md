PATCH

**The standalone executable starts again.** 1.5.0 was tagged but never published: its release job's smoke test
found that the executable built from it stopped at `ModuleNotFoundError: No module named 'platform'`. slipwai
loads the tool installer (`scripts/install-tools.py`) from its bundled assets at run time, so PyInstaller never
saw the standard-library modules it imports; they are now named in the build, and a test holds that list to the
installer's imports. 1.5.1 is the first release with everything 1.5.0 describes.
