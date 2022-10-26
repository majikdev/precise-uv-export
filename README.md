### Precise UV Export

The **Precise UV Export** add-on lets you export a pixel-perfect UV layout of a mesh to an image.<br>
Convenient for making low-resolution pixelated textures, where the default UV export is not ideal.

***Note:** This addon only works with Blender 3.0.0 or above.*

**How to install:**

1. Download the latest release or clone this repository.
2. Install `precise_uv_export.py` in Blender's preferences.
3. Enable the add-on.

**How to use:**

1. Open the `UV Editor` view.
2. Open the `UV` drop-down menu.
3. Press `Export Precise Layout`.

The exported image takes the size of the image in the editor, or 16x16.<br>
Each island in the UV layout is coloured in a different shade of grey.<br>
Pixels, where multiple UV islands overlap, are coloured in black.

*These settings can be changed during the exporting process.*
