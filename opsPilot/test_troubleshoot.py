"""
Quick test script for the troubleshooting feature.
Tests the AI troubleshoot handler without requiring full Flask app.
"""
from ai_shell_agent.ai_troubleshoot import ask_ai_for_troubleshoot

def test_troubleshoot():
    print("=" * 60)
    print("Testing Troubleshooting Feature")
    print("=" * 60)
    
    # Test Case 1: Nginx port conflict
    print("\n[Test 1] Nginx Port Conflict")
    print("-" * 60)
    error1 = "nginx: [emerg] bind() to 0.0.0.0:80 failed (98: Address already in use)"
    result1 = ask_ai_for_troubleshoot(error1)
    
    if result1 and result1.get("success"):
        plan = result1["troubleshoot_response"]
        print(f"✅ Analysis: {plan['analysis']}")
        print(f"✅ Risk Level: {plan['risk_level']}")
        print(f"✅ Diagnostic Commands: {len(plan['diagnostic_commands'])} commands")
        print(f"✅ Fix Commands: {len(plan['fix_commands'])} commands")
        print(f"✅ Verification Commands: {len(plan['verification_commands'])} commands")
    else:
        print(f"❌ Failed: {result1.get('error', 'Unknown error')}")
    
    # Test Case 2: Permission denied
    print("\n[Test 2] Permission Denied")
    print("-" * 60)
    error2 = "bash: /var/log/app.log: Permission denied"
    result2 = ask_ai_for_troubleshoot(error2)
    
    if result2 and result2.get("success"):
        plan = result2["troubleshoot_response"]
        print(f"✅ Analysis: {plan['analysis']}")
        print(f"✅ Risk Level: {plan['risk_level']}")
        print(f"✅ Fix Commands: {plan['fix_commands']}")
    else:
        print(f"❌ Failed: {result2.get('error', 'Unknown error')}")
    
    # Test Case 3: Disk full
    print("\n[Test 3] Disk Full")
    print("-" * 60)
    error3 = "No space left on device"
    context3 = {
        "last_command": "docker build .",
        "last_error": "write /var/lib/docker: no space left on device"
    }
    result3 = ask_ai_for_troubleshoot(error3, context=context3)
    
    if result3 and result3.get("success"):
        plan = result3["troubleshoot_response"]
        print(f"✅ Analysis: {plan['analysis']}")
        print(f"✅ Risk Level: {plan['risk_level']}")
        print(f"✅ Diagnostic Commands: {plan['diagnostic_commands']}")
        print(f"✅ Fix Commands: {plan['fix_commands']}")
    else:
        print(f"❌ Failed: {result3.get('error', 'Unknown error')}")
    
    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)

if __name__ == "__main__":
    test_troubleshoot()
