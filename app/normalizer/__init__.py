# app/normalizer/__init__.py
"""
Text Normalizer package.

Cleans and normalizes parsed text to ensure deterministic processing:
- Whitespace normalization
- Unicode normalization
- Bullet character standardization
- Header/footer removal
- Page number stripping

Same input always produces the same normalized output (PRD §5, §14).
"""
