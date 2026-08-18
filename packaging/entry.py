"""Frozen entry point.

PyInstaller wants a plain script, not a package. Keeping it here rather than
pointing the spec at ``mangame/__main__.py`` avoids a module that is both a
package member and a top-level bootstrap.
"""

import sys

from mangame.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
