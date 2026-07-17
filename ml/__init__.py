"""Isolated ML package for the Resume-to-Job Match Scorer.

Everything ML lives here (data generation, features, training, evaluation,
inference) with its own requirements.txt so the FastAPI backend never
depends on the ML stack. The backend imports only `ml.inference`.
"""
