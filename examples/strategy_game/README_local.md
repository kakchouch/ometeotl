# examples Strategy Game (Untracked Workspace Demo)

This folder contains a local-only implementation of a simple strategy game:
- shared deterministic engine
- CLI mode
- browser UI with SVG board and buttons

## Run CLI

From repository root:

```bash
python -m examples.strategy_game.cli
```

## Run Web UI

From repository root:

```bash
python -m examples.strategy_game.web_server
```

Then open:

- http://127.0.0.1:8765

## Local smoke tests

```bash
python -m pytest -q examples/strategy_game/test_engine_local.py
```

Notes:
- examples is ignored by git in this repository.
- no tracked source, docs, or test files are modified by this demo.
