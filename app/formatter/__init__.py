# app/formatter/__init__.py
"""
Output Formatter package.

Formats analysis results for Telegram display (Phase 7):
- Ranking table
- Detailed candidate reports
- Inline keyboard markup

Implements FR12 from the PRD. Handles Telegram message
length limits and MarkdownV2 escaping.
"""
