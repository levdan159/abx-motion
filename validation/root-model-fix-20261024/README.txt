Root project Ethernet 3D model loading fix —2026-10-24

The saved model references were enabled and their files existed. User's viewer
showed the new Ethernet pads without models; a viewer/cache or display-filter
cause could not be confirmed from the saved files alone.

The14 distinct model files for all61 new Ethernet footprints are now bundled
under abx-3dmodels/ethernet, referenced using ${KIPRJMOD}. Fresh paths also avoid
reusing previously failed model-cache entries. Native root PCB render confirms
RJ45, W5500 and support parts are rendered. Viewer runtime state still needs a
PCB/3D-view reload to read the updated references.

Verification:
- Exactly61 model path replacements, no other PCB text changed.
- All61 model references enabled and resolve from project-local files.
- BOM/CPL exclusion attributes preserved.
- Geometry, nets, traces, zones, pad data and model transforms unchanged.
- Fresh root-project native 3D render inspected: root-top.png.
- Existing root promotion audit passes with model paths normalized.

Stock STEP files are copied unmodified from installed KiCad libraries, with
copyright headers, license and credits preserved. Connector and buck WRL models
are dimension envelopes; they are not detailed vendor models.
