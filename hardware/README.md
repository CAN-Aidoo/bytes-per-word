# Hardware
- `cad/`: parametric CAD sources (for example CadQuery or OpenSCAD) and exported STL/STEP for 3D printing, with print settings.
- `electronics/`: KiCad project; ERC and DRC reports must be clean; BOM with part numbers and prices.
- `firmware/`: source, build instructions, pinned toolchain version.
- `measurements/`: raw logs written by instruments or firmware, never edited by hand. See `TEST_PROTOCOL.md`.
Agents design and check; humans build, flash and measure.
