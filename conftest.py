# Empty on purpose: its presence makes pytest add the repo root to sys.path,
# so `from app...` imports resolve under a bare `pytest` invocation (no root
# package/pyproject.toml otherwise puts the repo root on sys.path).
