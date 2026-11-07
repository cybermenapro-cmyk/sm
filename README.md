 
# SM Universal 0.5.0 Full Storage Manager

SM (Storage Management) is a portable C++17 language implementation. Source is tokenized, parsed into an AST, compiled to bytecode, then executed by a stack virtual machine. It does not interpret source one line at a time.

## Architecture

```text
SM Source (.sm) -> Lexer -> Parser -> AST -> Bytecode Compiler
    -> Stack VM -> Runtime -> Storage Manager -> std::filesystem
```

The source is portable. The installer builds a native executable for the current host with `g++` or `clang++`. The VM executes bytecode; this is not native machine-code JIT/AOT.

## Install

Requirements: Linux or Termux, Bash, and a C++17 compiler.

```bash
# Debian / Ubuntu
sudo apt install g++
# Termux
pkg install clang

bash scripts/install.sh
```

Installs into `~/sm`, with commands in `~/.local/bin`:

```bash
sm version
sm check examples/hello.sm
sm run examples/hello.sm
sm repl
```

Shortcuts: `smr file.sm`, `smi`, `smh`, `smv`. If needed, add `export PATH="$HOME/.local/bin:$PATH"` to your shell profile.

## Case-insensitive language and syntax

All language keywords, built-in commands, logical operators, variable names, function names, and parameter names are case-insensitive. `SHOW`, `show`, and `ShOw` are equivalent. `MyValue`, `MYVALUE`, and `myvalue` refer to the same variable.

Legacy and modern forms coexist:

| Existing syntax | Also supported |
|---|---|
| `VAR` | `LET`, `DECLARE`, implicit `name = value` |
| `SET` | `UPDATE` |
| `SHOW` | `PRINT`, `DISPLAY`, `OUTPUT` |
| `IF ... ELSE ... END` | `ELIF`, `ELSEIF` |
| `MKDIR` | `CREATE_DIR`, `DIRECTORY_CREATE` |
| `CREATE_FILE` | `FILE_CREATE`, `TOUCH` |
| `WRITE_FILE` | `FILE_WRITE`, `WRITE`, `WRITE_TO`, `WRITE_INTO` |
| `APPEND_FILE` | `FILE_APPEND`, `APPEND` |
| `READ_FILE` | `FILE_READ`, `READ` |
| `RENAME_FILE(old_path, destination_path)` | Existing explicit-path rename; modern `RENAME(old_path, "new-name.txt")` / `RENAME_TO` renames beside the source |
| `DELETE` | `DELETE_FILE`, `REMOVE` |

Logical operators: `AND`, `OR`, `NOT`. Comparisons: `==`, `!=`, `<`, `<=`, `>`, `>=`.

## Full Storage Manager

Every operation remains subject to the current operating-system user's permissions. SM does not bypass Linux permissions or obtain root access.

### Create, write, append, read, and clear

```sm
folder = /tmp/sm-demo/
file = /tmp/sm-demo/notes.txt
MKDIR(folder)
CREATE_FILE(file)

WRITE(file, "First version")       # Replace the complete file content
APPEND(file, " + added text")       # Add to the end
SHOW READ(file)
TRUNCATE(file)                      # Empty the file without deleting it
WRITE_FILE(file, "Legacy syntax")  # Old syntax remains available
```

`WRITE`, `WRITE_FILE`, `FILE_WRITE`, `WRITE_TO`, and `WRITE_INTO` overwrite the complete file. They prepare the new content in a temporary sibling file and then replace the target using filesystem rename behavior. For an existing symbolic link, the operation follows the link and updates its target. Existing permission bits are preserved where the host filesystem allows it. This reduces the chance of leaving a partially written file, but it is not a guarantee against power loss or every filesystem failure.

### Write at a byte position

Byte offsets start at **0**. `WRITE_AT` replaces bytes beginning at the offset with the supplied text; it can extend the file when the replacement reaches past its previous end. `INSERT_AT` inserts without removing existing bytes. `DELETE_RANGE` removes a byte range.

```sm
WRITE(file, "ABCDE")
WRITE_AT(file, 1, "xyz")   # AxyzE
INSERT_AT(file, 1, "++")   # A++xyzE
DELETE_RANGE(file, 1, 2)    # AxyzE
```

`INSERT_TEXT` aliases `INSERT_AT`; `OVERWRITE_AT` aliases `WRITE_AT`; `DELETE_AT` aliases `DELETE_RANGE`.

### Replace or delete a value inside a file

```sm
WRITE(file, "name=Saiko;mode=old;mode=old")
changed = REPLACE_TEXT(file, "mode=old", "mode=new")
removed = DELETE_TEXT(file, "Saiko")
SHOW changed
SHOW removed
```

`REPLACE_TEXT(file, old, new)` and `REPLACE_VALUE` replace every matching occurrence and return the number of replacements. `REPLACE` and `REPLACE_CONTENT` are aliases. `DELETE_TEXT(file, value)` and `DELETE_VALUE` remove every matching occurrence and return the number removed. The search value cannot be empty.

### Edit individual lines

Line numbers start at **1**, not 0. `WRITE_LINE` replaces an existing line. `INSERT_LINE` inserts before the selected line and accepts `line_count + 1` to append. `DELETE_LINE` removes one line.

```sm
WRITE(file, "red\ngreen\nblue")
WRITE_LINE(file, 2, "lime")
INSERT_LINE(file, 2, "yellow")
DELETE_LINE(file, 1)
SHOW READ_LINE(file, 1)
SHOW LINE_COUNT(file)
```

Aliases: `REPLACE_LINE` and `SET_LINE` for `WRITE_LINE`; `ADD_LINE` for `INSERT_LINE`; `REMOVE_LINE` for `DELETE_LINE`; `GET_LINE` for `READ_LINE`; `COUNT_LINES` for `LINE_COUNT`.

### Rename, move, copy, and safe delete

```sm
RENAME(file, "helio.txt")          # Rename in the same parent folder
MOVE(file, /tmp/another-folder/)  # Move into an existing directory
COPY(file, /tmp/backup/)          # Copy into an existing directory

SU OPERATION
    DELETE(file)
END_SU
```

`RENAME(old_path, "new-name.txt")` and `RENAME_TO` change only the final name and keep the source parent folder. Supplying a destination path with a parent directory uses that destination path. The legacy `RENAME_FILE(old_path, destination_path)` keeps its original explicit-destination behavior. `MOVE` also keeps explicit-destination behavior and accepts an existing directory as the destination. `COPY` accepts an existing destination directory too.

`DELETE` still requires an active `SU SESSION`, `SU BLOCK`, or `SU OPERATION` scope. It moves the target into `.sm_trash` under the current working directory; it does **not** permanently erase it. `SU` is an SM-level scope, not OS root access.

### Directory and path tools

- `MKDIR(path)` / `CREATE_DIR(path)` create directories.
- `LIST_DIR(path)` returns a sorted, newline-separated string; directory names end in `/`.
- `ENTRY_COUNT(path)` returns the number of immediate directory entries.
- `LIST_RECURSIVE(path)` / `LIST_TREE(path)` lists descendants recursively.
- `RECURSIVE_COUNT(path)` / `COUNT_RECURSIVE(path)` count descendants; `DIRECTORY_SIZE(path)` / `DIR_SIZE(path)` total regular-file bytes recursively.
- `EXISTS(path)`, `IS_FILE(path)`, `IS_DIR(path)`, `IS_EMPTY(path)` inspect paths.
- `FILE_SIZE(path)` / `SIZE(path)` return bytes for regular files.
- `FREE_SPACE(path)` / `AVAILABLE_SPACE(path)` and `TOTAL_SPACE(path)` return byte counts reported by the filesystem.
- `FILENAME(path)`, `EXTENSION(path)`, `PARENT_PATH(path)`, `ABSOLUTE_PATH(path)`, and `PATH_KIND(path)` inspect path components.
- `DEVICE(path)` remains a read-only block/character-device type check.

Paths ending in `/` are inferred as directories; other paths are inferred as files. Quoted paths are supported. Use spaces around division operators to avoid path-literal ambiguity.

## Language features

```sm
let UserName = "Saiko"
VAR score = 88

if SCORE >= 90
    show "Excellent, " + username
elseif score >= 70 aNd not false
    PRINT "Good progress, " + USERNAME
else
    DISPLAY "Keep going"
end

FUNC addBonus(value)
    RETURN value + 5
END
show addbonus(score)
```

Functions, `IF` / `ELIF` / `ELSE`, and `WHILE` are compiled to bytecode before execution. `AND` and `OR` currently evaluate both operands (no short-circuit evaluation).

## Diagnostics

- `SM001`: command / source loading errors
- `SM201`: lexical or syntax errors
- `SM301`: runtime errors, including invalid storage arguments and filesystem failures

## Build and test

```bash
g++ -std=c++17 -O2 -DNDEBUG -Wall -Wextra -pedantic src/sm.cpp -o sm
bash tests.sh
```

## Current limits

SM provides file, directory, and content-management operations through C++17 `std::filesystem` and standard streams. It does not provide raw-device writes, partitioning/formatting, OS root integration, a native machine-code JIT/AOT compiler, or persistent bytecode. `DEVICE(path)` is read-only. Byte-oriented edits use byte offsets, not Unicode character indices. Line-based edits normalize CRLF line endings to LF. Filesystem operations remain subject to OS permissions and filesystem-specific behavior.
