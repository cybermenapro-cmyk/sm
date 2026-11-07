# SM Language Specification (Draft)

Version: 0.1.0-beta  
Status: Draft for the beta implementation

## 1. Identity

SM means **Storage Management**. It is an independent interpreted language focused on storage systems and data management. The first implementation is a reference interpreter; the host implementation language does not define SM syntax or semantics.

## 2. Approved architecture decisions

- Execution: interpreted.
- Scope: hybrid storage-level and data-level language.
- Variables: dynamic typing.
- Collections: `LIST` and `ARRAY` are distinct.
- Array indexes: zero-based.
- Data lifetime: temporary and persistent.
- Permission syntax: `SU SESSION`, `SU BLOCK`, `SU OPERATION`.

## 3. Lexical conventions

- Source file extension: `.sm`.
- UTF-8 source text.
- Keywords are case-insensitive in Beta; examples use uppercase.
- Identifiers match `[A-Za-z_][A-Za-z0-9_]*`.
- A `#` outside a string begins a comment through end of line.
- Strings use double quotes.

## 4. Values

| Value kind | Example | Notes |
|---|---|---|
| STRING | `"Saiko"` | UTF-8 text |
| INTEGER | `15` | Whole number |
| FLOAT | `2.5` | Decimal number |
| BOOLEAN | `TRUE`, `FALSE` | Logical value |
| NULL | `NULL` | Empty value |
| SIZE | `512 MB` | Native byte quantity |
| LIST | `["a", 2, TRUE]` | Dynamic length, mixed values |
| ARRAY | `ARRAY(3)` | Fixed length, indexes start at zero |
| OBJECT | `{"name": "disk1"}` | String-keyed record |

Decimal units: B, KB, MB, GB, TB (powers of 1000).  
Binary units: KiB, MiB, GiB, TiB (powers of 1024).

## 5. Variables and collections

```sm
VAR owner = "Saiko"
SET owner = "Saiko INA"
LIST mixed = ["x", 10, TRUE]
ARRAY blocks = ARRAY(2)
SET blocks[0] = 64 MB
OBJECT disk = {"name": "disk1", "capacity": 512 GB}
SHOW disk.capacity
SET disk.capacity = 1 TB
```

`VAR` declares or replaces a binding in the active scope in this beta prototype. `SET` changes an existing binding, an array slot, or an object field. A closed DATA block is also available as an object named after the block. `LIST` requires a list literal. `OBJECT` requires an object literal. `ARRAY(n)` creates exactly `n` slots initialized to `NULL`.

## 6. Data blocks

```sm
DATA TEMP cache
    VAR hits = 1
END_DATA

DATA PERSIST preferences
    VAR owner = "Saiko"
END_DATA
SAVE preferences
LOAD preferences
```

Temporary blocks live only in the current interpreter process. Persistent blocks are serialized to JSON in the workspace's `.sm-data` directory when `SAVE` is called.

## 7. Storage instructions

```sm
DEVICE LIST
DEVICE INFO "."
FILE CREATE "notes/a.txt"
FILE WRITE "notes/a.txt" "hello"
FILE APPEND "notes/a.txt" " world"
FILE READ "notes/a.txt"
FILE INFO "notes/a.txt"
FILE EXISTS "notes/a.txt"
FILE SIZE "notes/a.txt"
DIRECTORY CREATE "backup"
DIRECTORY LIST "backup"
DIRECTORY INFO "backup"
COPY "notes/a.txt" TO "backup/a.txt"
MOVE "backup/a.txt" TO "backup/final.txt"
VERIFY "notes/a.txt" AGAINST "backup/final.txt" WITH SHA256
TRASH "backup/final.txt"
RESTORE "backup/final.txt"
QUOTA CHECK "backup" LIMIT 100 MB
```

All paths are relative to the workspace. Absolute paths and paths that resolve outside it are rejected. Device inspection is read-only; `DEVICE LIST` reports the filesystem volume hosting the workspace, not a full list of physical devices. Copy/move do not overwrite destinations.

## 8. Storage plans

```sm
PLAN "plan-name"
    FILE WRITE "notes/planned.txt" "preview"
END_PLAN

APPLY "plan-name"
```

`PLAN` stores supported operation lines and prints a preview without executing them. `APPLY` asks for confirmation and then executes the plan. Beta's plan system is sequential and is not yet a transactional rollback engine.

## 9. Permission requests

```sm
SU SESSION
    DEVICE LIST
END_SU

SU BLOCK
    DEVICE LIST
END_SU

SU OPERATION DEVICE LIST
```

The syntax represents requested scope. In Beta 0.1.0, the interpreter only records the request and does not acquire host privileges. No password is collected. No root escalation is attempted.

## 10. Errors

Errors are reported with the source line where possible. A failed operation stops execution. Beta diagnostics are basic and will be expanded alongside the formal parser.

## 11. Non-goals of Beta

- Raw block-device writes.
- Formatting or partitioning disks.
- Mounting or unmounting filesystems.
- Automatic privilege escalation.
- Production guarantees, transactional rollback, or network storage orchestration.
