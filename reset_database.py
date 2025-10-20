#!/usr/bin/env python3
"""
Database Reset Utility

This script resets the CI/CD database and recreates it with the latest schema.
Use this if you encounter database schema issues during development.
"""

import os
import sys
from pathlib import Path

def reset_cicd_database():
    """Reset the CI/CD database."""
    db_path = Path("ai_shell_agent/data/cicd.db")
    
    print("🗄️  CI/CD Database Reset Utility")
    print("=" * 40)
    
    if db_path.exists():
        print(f"📁 Found existing database: {db_path}")
        
        # Ask for confirmation
        response = input("⚠️  This will delete all Jenkins/Ansible configs and build logs. Continue? (y/N): ")
        if response.lower() != 'y':
            print("❌ Reset cancelled.")
            return False
        
        # Backup old database
        backup_path = db_path.with_suffix('.db.backup')
        if backup_path.exists():
            backup_path.unlink()  # Remove old backup
        
        db_path.rename(backup_path)
        print(f"💾 Backed up old database to: {backup_path}")
        print(f"🗑️  Removed old database: {db_path}")
    else:
        print("📁 No existing database found.")
    
    # Import and initialize new database
    print("🔧 Creating new database with latest schema...")
    
    try:
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from ai_shell_agent.modules.cicd.models import DatabaseManager
        
        # This will create the database with the latest schema
        db_manager = DatabaseManager()
        print("✅ New database created successfully!")
        
        # Verify tables
        tables = db_manager.execute_query("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        
        print(f"📋 Created tables: {[t['name'] for t in tables]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating database: {e}")
        return False

if __name__ == "__main__":
    success = reset_cicd_database()
    
    if success:
        print("\n🎉 Database reset complete!")
        print("You can now restart your OpsPilot server and try the Jenkins connection again.")
    else:
        print("\n💥 Database reset failed!")
        print("Check the error messages above and try again.")
    
    sys.exit(0 if success else 1)