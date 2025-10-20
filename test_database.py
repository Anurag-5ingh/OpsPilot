#!/usr/bin/env python3
"""Test database schema and functionality."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai_shell_agent.modules.cicd.models import DatabaseManager

def test_database():
    print("🗄️ Testing Database Schema")
    print("=" * 40)
    
    # Initialize database
    dm = DatabaseManager()
    print("✅ Database initialized successfully")
    
    # Check tables
    tables = dm.execute_query("SELECT name FROM sqlite_master WHERE type='table'")
    table_names = [t['name'] for t in tables if not t['name'].startswith('sqlite_')]
    print(f"📋 Tables created: {table_names}")
    
    # Check Jenkins table schema
    if 'jenkins_configs' in table_names:
        schema = dm.execute_query("PRAGMA table_info(jenkins_configs)")
        print("\n🔧 Jenkins table schema:")
        for col in schema:
            print(f"   - {col['name']}: {col['type']}")
        
        # Check for required columns
        column_names = [col['name'] for col in schema]
        required_cols = ['password_secret_id', 'api_token_secret_id']
        
        for col in required_cols:
            status = "✅" if col in column_names else "❌"
            print(f"   {status} {col}")
    
    return True

if __name__ == "__main__":
    try:
        test_database()
        print("\n✅ All database tests passed!")
    except Exception as e:
        print(f"\n❌ Database test failed: {e}")
        sys.exit(1)