# SM Beta

**SM (Storage Management)** is an independent, interpreted domain-specific programming language for storage and data workflows. This repository contains the first reference interpreter, written in Python using only the standard library. Python is the implementation language of this interpreter; it is not the syntax or language users write.

> Status: experimental beta. Do not use for important data or production administration.

## What is included in Beta 0.1.0

- Dynamic variables: `VAR`, `SET`, `LIST`, `OBJECT`.
- Fixed-length arrays with zero-based indexing: `ARRAY name = ARRAY(n)`.
- Native storage-size values: `B`, `KB`, `MB`, `GB`, `TB`, `KiB`, `MiB`, `GiB`, `TiB`.
- Temporary and persistent data blocks: `DATA TEMP`, `DATA PERSIST`, `SAVE`, `LOAD`.
- File and directory operations inside an SM workspace.
- `COPY`, `MOVE`, SHA-256 `VERIFY`, recoverable `TRASH` and `RESTORE`.
- `QUOTA CHECK` for reporting folder usage against a limit.
- `DEVICE LIST` and `DEVICE INFO` for read-only capacity reporting.
- Named `PLAN` blocks and explicit `APPLY` confirmation.
- `SU SESSION`, `SU BLOCK`, and `SU OPERATION` permission-request syntax.

## Requirements

- Python 3.10 or later
- No third-party packages

## Run

From this directory:

```bash
python3 sm.py --version
python3 sm.py examples/quickstart.sm
```

SM creates a `.sm-workspace/` directory in the current working directory. Relative file paths in SM programs are confined to this workspace. Absolute paths and path traversal outside the workspace are rejected.

Run the permission syntax example:

```bash
python3 sm.py examples/su_demo.sm
```

Check basic block structure without executing the program:

```bash
python3 sm.py --check examples/quickstart.sm
```

## First program

```sm
PROGRAM "Hello Storage"

VAR owner = "Saiko"
VAR capacity = 512 GB
LIST items = ["backup", 12, TRUE]
ARRAY blocks = ARRAY(2)
SET blocks[0] = 64 MB
SET blocks[1] = 128 MB

SHOW owner
SHOW capacity
SHOW items[0]
SHOW blocks[1]
SET blocks[1] = 256 MB

DIRECTORY CREATE "notes"
FILE WRITE "notes/hello.txt" "Hello from SM"
FILE READ "notes/hello.txt"

END
```

## Storage Intent Engine

A `PLAN` block stores operations without performing them. `APPLY` prints a review prompt and requires confirmation unless the CLI is explicitly invoked with `--yes`.

```sm
PLAN "weekly-backup"
    COPY "notes/hello.txt" TO "notes/hello-copy.txt"
    VERIFY "notes/hello.txt" AGAINST "notes/hello-copy.txt" WITH SHA256
END_PLAN

APPLY "weekly-backup"
```

## Data persistence

`DATA TEMP` is runtime-only. `DATA PERSIST` remains in memory until saved. `SAVE` writes JSON data under `.sm-workspace/.sm-data/`; `LOAD` restores it in a later run.

```sm
DATA PERSIST settings
    VAR owner = "Saiko"
    VAR limit = 20 GB
END_DATA

SAVE settings
LOAD settings
SHOW settings.owner
```

## Safety model and current limitations

- SM Beta does not run shell commands, external programs, or arbitrary Python code.
- File and directory operations are confined to the workspace. Use test data only.
- `TRASH` moves items into `.sm-workspace/.sm-trash/`; `RESTORE` can recover them to the original relative path.
- `COPY` and `MOVE` refuse to overwrite an existing destination.
- `DEVICE LIST` currently reports the filesystem volume that contains the SM workspace; it does not enumerate physical disks. Device reporting is read-only. Raw disk writes, formatting, partitioning, mount changes, and filesystem repair are not implemented.
- `SU` currently records a scoped permission request only. **It does not invoke `sudo`, ask for a password, or obtain OS root privileges.** A future privileged adapter would need explicit host authorization and a separate security review.
- `--check` currently validates block counts, not the full grammar.
- This beta is a prototype, not a production-grade storage manager. Back up important data independently.

## Design principles

1. Storage-aware values are native language values.
2. Preview before applying multi-step storage changes.
3. Verify copied data rather than assuming success.
4. Prefer reversible deletion.
5. Keep host privileges separate from language syntax.
6. Keep the language specification independent of the interpreter implementation.

## Roadmap

- **0.1.0 Beta:** reference interpreter, variables, collections, paths, basic storage operations, preview plans, data persistence.
- **0.2:** formal lexer/parser and source-location diagnostics; functions, conditions, loops, and modules.
- **0.3:** event/watch model, quota enforcement policies, stronger transactions and rollback.
- **0.4:** pluggable storage backends and a permission-provider interface.
- **1.0:** stable language specification, compatibility tests, packaging, and security review.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Bug reports should include the SM source file, expected behavior, actual behavior, OS, and Python version. Never attach passwords, private keys, or personal data.

## License

MIT. See [LICENSE](LICENSE).
