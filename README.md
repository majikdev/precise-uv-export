### Precise UV Export

The **Precise UV Export** add-on lets you export a pixel-perfect UV layout of a mesh to an image.<br>
Convenient for making low-resolution pixelated textures, where the default UV export is not ideal.

***Note:** This addon only works with Blender 3.0.0 or above.*

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
