# Artwork

One PNG is the source of truth. mangame derives everything else.

## Users: drop in a PNG

Put a PNG named for the manga directly in the user emblem directory:

```text
emblems/Hunter x Hunter.png
```

On the next refresh, mangame folds the filename to `hunter-x-hunter` and
creates:

```text
emblems/hunter-x-hunter/ready.png
emblems/hunter-x-hunter/due.png
emblems/hunter-x-hunter/break.png
```

The source PNG remains at the root. Replacing it regenerates the three files;
removing the emblem in Settings removes both source and generated output.

The paths are:

- Linux: `~/.local/share/mangame/emblems/`
- Windows: `%APPDATA%\mangame\emblems\`
- macOS: `~/Library/Application Support/mangame/emblems/`

`MANGAME_HOME` and `MANGAME_EMBLEM_DIR` override those locations as documented
in the README. Settings → Artwork remains available when using a file picker
is more convenient.

The three generated states are fixed:

- **ready** — the original colour image;
- **due** — a mid-grey version;
- **break** — a near-black silhouette with a near-white rim.

There is no renderer choice. The contrasting rim keeps the break icon visible
on both light and dark panels.

## Contributors: add one PNG

Bundled artwork follows the same rule. Add an original PNG to `artwork/`:

```text
artwork/my-emblem.png
```

Then run:

```bash
uv run python tools/gen_icons.py
uv run python tools/gen_icons.py --check
```

Generated files live under `src/mangame/assets/emblems/` and must not be edited
by hand. The generator needs only the normal Python development environment;
Inkscape and ImageMagick are not required.

Qt scales one 256px image per state to the panel's requested size. Keeping
twelve nearly identical PNG resolutions added thousands of files to a large
library without a visible benefit, so mangame no longer stores that ladder.
Installer `.ico` and `.icns` containers still contain the sizes required by
Windows and macOS; that is separate from manga tray artwork.

Only contribute original work that may be distributed under the repository's
MIT licence. Do not add copied character art, covers, publisher marks or
series logos.
