# SM Language - public launch strategy

## Positioning

**Tagline:** Storage-first scripting. Preview it. Verify it. Manage it.

**One-sentence pitch:** SM is an interpreted language that makes storage sizes, file workflows, data persistence, integrity checks, and reviewable storage plans first-class parts of one small syntax.

Do not advertise SM as universally faster or as the first language to support a feature until reproducible benchmarks and a careful prior-art review exist.

## Who should try the first beta

Start with a narrow audience:

- Linux learners and hobbyists.
- Homelab and self-hosting users.
- Developers who write repeatable file and backup workflows.
- People interested in language design and interpreters.

Avoid marketing Beta 0.1 as a production disk-management tool. Its current device view is read-only and its operations are workspace-sandboxed.

## The 30-day launch sequence

### Days 1-3: make the repository understandable

- Publish the repository with `README.md`, `SPEC.md`, `LICENSE`, `CONTRIBUTING.md`, and `CODE_OF_CONDUCT.md`.
- Put the quick-start program near the top of the README.
- State the beta limitations clearly, especially the Python runtime dependency and the fact that `SU` does not elevate privileges yet.
- Add issue templates for bug reports and feature requests.

### Days 4-7: show one complete use case

Record a 45-60 second demo that shows:

1. `VAR capacity = 512 GB`.
2. `FILE WRITE` and `COPY`.
3. `VERIFY ... WITH SHA256`.
4. A `PLAN` preview followed by an explicitly confirmed `APPLY`.
5. `TRASH` and `RESTORE`.

Use the same code in the README, demo, and downloadable example. A working demonstration is more persuasive than claims about revolutionary technology.

### Week 2: find the first testers

- Invite 5-10 developers or Linux learners to try the quick-start on their own test folders.
- Ask them to complete one task and report where syntax was confusing.
- Turn repeated confusion into documentation fixes.
- Label a few small issues `good first issue` only when they are genuinely self-contained.

### Week 3: improve reliability before adding many features

- Fix bugs reported by testers.
- Add tests for each fixed bug.
- Improve error messages and examples.
- Keep changes small and publish a changelog.

### Week 4: ship Beta 0.1.1

- Publish a short release note listing fixes and remaining limitations.
- Share the same short demo in developer communities where language design, Linux, and open source projects are welcome.
- Ask for one specific kind of feedback, such as syntax clarity or the storage-plan workflow.

## What to measure

Track useful adoption, not just attention:

- People who successfully run the quick-start.
- Repeat testers who use SM for a second task.
- Reproducible bug reports and time to fix them.
- External examples, issues, and pull requests.
- The number of users who understand the limitations before trying the beta.

Stars and views can help discovery, but they are not proof that a language is useful.

## Benchmark strategy

Do not publish a speed claim yet. Beta 0.1 is a Python-hosted reference interpreter and has not been benchmarked.

Before claiming performance, define identical tasks and test data, publish the exact hardware and software versions, run multiple trials, and compare equivalent results. Include startup time, throughput, memory use, and correctness checks. Consider a Rust runtime only after the language semantics and test suite are stable.

## Product milestones

- **0.1.0:** prove the syntax and basic workspace workflows.
- **0.1.1:** fix real tester feedback and improve diagnostics.
- **0.2:** formal lexer/parser, conditions, loops, functions, and stronger tests.
- **0.3:** reliable watch/events, quota policies, and transactional operations.
- **0.4:** permission-provider interface and pluggable storage backends.
- **1.0:** stable specification, documented compatibility rules, security review, and measured performance.

## Launch principle

Make a small tool that reliably solves one storage task, demonstrate it honestly, listen to users, and improve it in public. A community grows from repeated usefulness, not from promising that a new language will replace every existing one.
