"""Streamlit entry point for the AI Oral Pathology assistant."""
#commit
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent
APP_DIR = ROOT_DIR / "DisHekimligiAI"

if APP_DIR.exists() and str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

# Redirect to home page
st.switch_page("pages/0_home.py")

