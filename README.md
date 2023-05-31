### Precise UV Export

**Precise UV Export** is an add-on for Blender 3.0.0 or above. It lets you export a pixel-perfect UV layout of a mesh to an image. Convenient for making low-resolution pixelated textures, where the default UV export is not ideal.

**How to install:**

1. Download the latest release or clone this repository.
2. Install `precise_uv_export.py` in Blender's preferences.
3. Enable the add-on.

**How to export:**

1. Open the `UV Editor` view.
2. Open the `UV` drop-down menu.
3. Press `Export Precise Layout`.

**Export settings:**

* **Image Size** - specify the width and height of the exported image.
* **Shade Islands** - fill each island with a different shade of grey.
* **Grid Overlay** - overlay a checkerboard pattern to make referencing the model easier.
* **Show Overlap** - colour pixels with multiple overlapping islands black (inconsistent).
