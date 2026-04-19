# v2 vendor directory

Drop the following files here to enable v2 generation. The generator inlines
them into the single-file HTML artifact. No network fetch is ever performed.

## Required

- `react.production.min.js`
  Source: https://unpkg.com/react@18/umd/react.production.min.js
- `react-dom.production.min.js`
  Source: https://unpkg.com/react-dom@18/umd/react-dom.production.min.js

## Optional (typography)

v2 uses Plus Jakarta Sans, Source Sans 3, and JetBrains Mono. If you drop the
TTF files below, the generator embeds them as base64 @font-face rules. If any
font is absent, the generator falls back to the system stack silently.

- `PlusJakartaSans-Variable.ttf`
  Source: https://fonts.google.com/specimen/Plus+Jakarta+Sans
- `SourceSans3-Variable.ttf`
  Source: https://fonts.google.com/specimen/Source+Sans+3
- `JetBrainsMono-Variable.ttf`
  Source: https://fonts.google.com/specimen/JetBrains+Mono

## Verification

Download offline, verify SHA256 if publishing, commit the files. The generator
enforces a minimum file size on the React UMDs to catch empty or truncated
drops.

## Failure mode

Without `react.production.min.js` or `react-dom.production.min.js`, running
`python3 -m aigovclaw.hub.v2.cli generate` exits with code 2 and prints a
maintainer-action message naming the missing file. No network fetch is
attempted.
