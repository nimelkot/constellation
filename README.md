# Constellation

Constellation is a local-first terminal workspace for exploring concurrent agent threads as a dependency graph. It provides a persistent SQLite tree, a Textual dual-pane interface, and an MCP client boundary that keeps transport concerns separate from orchestration.

## Quick start

```console
python -m pip install -e .
constellation run "Investigate the flaky test" --interactive
constellation forest
constellation branch --resume <node-id>
```

The default database is `.constellation/state.db`. Set `CONSTELLATION_DB` to use another location.
