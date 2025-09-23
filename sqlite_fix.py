"""
SQLite compatibility fix for Streamlit Cloud
This module replaces the system sqlite3 with pysqlite3 to meet ChromaDB requirements
"""

__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')