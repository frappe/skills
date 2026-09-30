# E02 — File upload validation

**Scope:** what the app accepts as an upload.

**Why:** upload validation decides the content type, the extension, and where the file lands.

## Find
- Extension and content-type checks: allowlist or denylist? Is the check on the client only?
- Content sniffing vs declared type; double extensions; null bytes; unicode in filenames.
- SVG, HTML, and XML uploads — these execute or expand (XXE) when served or parsed.
- Size limits, and whether they are enforced before the file is buffered in memory.
- Image processing paths (Pillow, `convert_to_webp`) — decompression bombs and format-specific
  parser bugs; also an SSRF sink, see `F01`.
- EXIF/metadata stripping on images.
- Antivirus or content scanning, if the deployment claims it.

## Confirm
- Pair each gap with where the file is later served or parsed — an unvalidated upload that is
  only ever downloaded with `Content-Disposition: attachment` is much lower severity.

## Report
State the accepted payload and the serving route.
