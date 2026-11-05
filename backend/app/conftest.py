
"""
Pytest setup: keep tests away from the configured application database.
"""
import os

# This must be set before tests import app.main or app.database.session.
os.environ["DATABASE_URL"] = "sqlite:///./sportsiq_test.db"
