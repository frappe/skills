---
id: E01
area: files-paths
---
# E01 — Path traversal on read and write

**Scope:** file reads, and file creation, move, rename, and delete, where any part of the path
comes from a request.

**Why:** a name that reaches a file path is a read primitive, and a fix that guards one source
of path segments often misses another. The same path handling on the write side gives arbitrary file
write, and a write that lands in an imported or served location is code execution.

Read and write share one guard analysis — the containment check is the same code — so they are
one scope.

## Find — read
- `rg -n "open\(|os\.path\.join|send_file|read_file|get_file_path|Path\(" --type py` and
  filter to calls whose path argument is non-constant.
- Frappe-specific sources of path segments: `Module Def` name, app name, doctype name,
  `File.file_url`, `File.file_name`, print format name, template name, translation file,
  license/readme viewers, SCORM/zip entry names, backup file names.

## Find — write
- Upload handlers, import handlers, backup/restore, `File.save_file`, `write_file`,
  `os.rename`, `shutil.move`, `os.remove`, zip and tar extraction.
- Zip and tar entry names (`../`, absolute paths, symlinks) are a traversal sink on both sides.
- Filename construction: is the client-supplied `file_name` sanitised, or only the extension
  checked? Data-URI uploads carry their own filename field — check it separately.
- Any write to a path under `apps/`, `sites/assets/`, `sites/*/public/`, or a `.py`/`.js`
  location — that is code execution, not just a file write.
- SQL primitives that write files — `INTO OUTFILE`, `INTO DUMPFILE`. Read the driver flags and
  the query sanitiser yourself; `B04` judges whether the injection reaches them, you judge where
  the file lands.

## Confirm
- Check the guard: is it `..` string matching (bypassable by encoding, `....//`, or absolute
  paths), or a resolved-path containment check (`os.path.realpath(...).startswith(base)`)?
- Confirm the base directory is the site directory, not the bench directory.
- Prove the resulting path escapes the intended directory, or lands somewhere executable.

## Report
Give the traversing input that reaches a file outside the site. Critical if a write lands
anywhere that is later imported, executed, or served as HTML.
