# app/bot/__init__.py
"""
Telegram Bot package.

Contains all Telegram-specific logic:
- Command handlers (/start, /help, /reset, /process)
- Document upload handlers
- Session management
- Message formatting for Telegram display

This layer is a thin adapter — it translates Telegram events into
calls to the service layer and formats responses back to the user.
No business logic should live here.
"""
