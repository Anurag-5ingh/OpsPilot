#!/usr/bin/env python3
"""Test API endpoints functionality."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai_shell_agent.modules.cicd import JenkinsConfig, JenkinsService

def test_api_components():
    print("🔌 Testing API Components")
    print("=" * 40)
    
    # Test Jenkins config creation
    print("📝 Testing Jenkins config creation...")
    config = JenkinsConfig(
        user_id="test_user",
        name="Test Jenkins",
        base_url="https://jenkins.example.com",
        username="test_user"
    )
    
    # Set fallback credentials (simulating keyring failure scenario)
    config._fallback_password = "test_password"
    config._fallback_token = "test_token"
    
    print(f"✅ Jenkins config created: {config.name}")
    print(f"   - URL: {config.base_url}")
    print(f"   - Username: {config.username}")
    print(f"   - Has fallback password: {hasattr(config, '_fallback_password')}")
    print(f"   - Has fallback token: {hasattr(config, '_fallback_token')}")
    
    # Test service initialization
    print("\n🔧 Testing Jenkins service initialization...")
    try:
        service = JenkinsService(config)
        print("✅ Jenkins service initialized successfully")
        print(f"   - Base URL: {service.base_url}")
        print(f"   - Username: {service.username}")
        print(f"   - Has session: {hasattr(service, '_session')}")
        print(f"   - SSL verification disabled: {not service._session.verify}")
        
        service.close()
        print("✅ Service closed properly")
        
    except Exception as e:
        print(f"❌ Service initialization failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    try:
        success = test_api_components()
        if success:
            print("\n✅ All API component tests passed!")
        else:
            print("\n❌ Some tests failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ API test failed: {e}")
        sys.exit(1)