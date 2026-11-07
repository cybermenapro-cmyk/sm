# SM Beta 0.1.0

## First public prototype

This is the first executable prototype of the SM language.

### Highlights

- A standalone `.sm` source format with dynamic variables and storage-aware `SIZE` values.
- Separate dynamic `LIST` and fixed-size, zero-indexed `ARRAY` collections.
- `DATA TEMP` and `DATA PERSIST` blocks.
- A sandboxed workspace for file and directory operations.
- Named `PLAN` / `APPLY` workflows, SHA-256 file verification, reversible Trash, and quota reports.
- Read-only storage capacity inspection.
- Initial `SU` scope syntax, without host privilege escalation.

### Known limitations

- The parser and diagnostics are intentionally small; conditionals, loops, functions, modules, and a formal standalone grammar parser are not included yet.
- `QUOTA CHECK` reports usage; it does not enforce a hard operating-system quota.
- Plans are sequential and do not support automatic rollback.
- `SU` records a request but does not grant Root privileges.
- Device access is inspection-only.

### Compatibility

Python 3.10+ is required for the reference interpreter. The `.sm` language design remains independent of Python.
