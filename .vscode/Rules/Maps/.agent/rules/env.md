---
trigger: always_on
---

# Environment Configuration
When executing Python commands, ALWAYS use the local virtual environment. 
Use the interpreter located at `./.venv/bin/python` (or `.\.venv\Scripts\python.exe` on Windows).
Do not use Conda or run python directly from the global path.