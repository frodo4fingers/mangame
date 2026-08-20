## What changed

<!-- State the user-visible outcome and why this is the smallest complete fix. -->

## Evidence

<!-- Name the regression test, reproduction, screenshot or measurement. -->

## Checklist

- [ ] The change is focused and does not include unrelated cleanup.
- [ ] A bug fix has a test that fails without the fix.
- [ ] Tests use neither the network nor a real display.
- [ ] User-visible behaviour and contributor instructions are documented.
- [ ] `CHANGELOG.md` is updated when users need to know about the change.
- [ ] The full gate from `CONTRIBUTING.md` passes.
- [ ] UI or artwork changes include before/after images.
- [ ] Artwork changes pass `uv run python tools/gen_icons.py --check` and update
      `docs/icon-reference.png` intentionally.
