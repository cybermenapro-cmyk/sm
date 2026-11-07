# Contributing to SM

Thanks for considering a contribution.

## Before opening an issue

- Search existing issues for duplicates.
- Use a minimal `.sm` example that reproduces the behavior.
- Include expected output, actual output, operating system, and Python version.
- Remove passwords, tokens, private keys, and personal data from logs.

## Development

SM Beta uses Python's standard library. Run the test suite with:

```bash
python3 -m unittest discover -s tests -v
```

Run the demo from the repository root:

```bash
python3 sm.py examples/quickstart.sm
```

## Contribution guidelines

- Keep SM syntax independent of Python syntax and implementation details.
- Add tests for every language feature or bug fix.
- Preserve workspace path restrictions.
- Do not add shell execution or implicit privilege escalation.
- Document syntax changes in `SPEC.md` and user-facing changes in `README.md`.
- Prefer small, focused pull requests.
