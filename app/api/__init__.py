# app/api/__init__.py
"""
API package.

Contains FastAPI route definitions. The API layer provides HTTP endpoints
for health checks, and in future phases, for programmatic access to
upload, process, and candidate report features.

This layer is an alternative interface to the same service layer
that the Telegram bot uses, enabling future web dashboard integration (PRD §17).
"""
