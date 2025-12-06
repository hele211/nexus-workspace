"""
Verification script for backend foundation (Steps 1-3).

Run from project root:
    source spoon-env/bin/activate
    python -m backend.verify_setup
"""

import sys
from datetime import datetime


def mask_key(key: str) -> str:
    """Mask API key, showing only first/last 4 chars."""
    if not key or len(key) < 12:
        return key if key else "(not set)"
    return f"{key[:4]}...{key[-4:]}"


def test_config():
    """Test Step 1: config.py"""
    print("\n" + "=" * 50)
    print("Step 1: Testing config.py")
    print("=" * 50)
    
    try:
        from backend.config import (
            LLM_PROVIDER,
            MODEL_NAME,
            OPENAI_API_KEY,
            GEMINI_API_KEY,
            NCBI_EMAIL,
            NCBI_API_KEY,
            SUPABASE_URL,
            SUPABASE_KEY,
        )
        
        print(f"  LLM_PROVIDER:    {LLM_PROVIDER}")
        print(f"  MODEL_NAME:      {MODEL_NAME}")
        print(f"  OPENAI_API_KEY:  {mask_key(OPENAI_API_KEY)}")
        print(f"  GEMINI_API_KEY:  {mask_key(GEMINI_API_KEY)}")
        print(f"  NCBI_EMAIL:      {NCBI_EMAIL or '(not set)'}")
        print(f"  NCBI_API_KEY:    {mask_key(NCBI_API_KEY)}")
        print(f"  SUPABASE_URL:    {SUPABASE_URL or '(not set)'}")
        print(f"  SUPABASE_KEY:    {mask_key(SUPABASE_KEY)}")
        
        print("\n✅ Config loaded successfully")
        return True
        
    except ImportError as e:
        print(f"\n❌ Config import failed: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Config error: {e}")
        return False


def test_common_schemas():
    """Test Step 2: schemas/common.py"""
    print("\n" + "=" * 50)
    print("Step 2: Testing schemas/common.py")
    print("=" * 50)
    
    try:
        from backend.schemas.common import PageContext, AgentResponse
        
        # Test PageContext
        page_ctx = PageContext(
            route="/experiments",
            workspace_id="ws_test123",
            user_id="user_abc",
            experiment_ids=["exp_001"],
            filters={"status": "active"}
        )
        print(f"  PageContext created: route={page_ctx.route}")
        
        # Test serialization
        json_str = page_ctx.model_dump_json()
        print(f"  PageContext JSON length: {len(json_str)} chars")
        
        # Test AgentResponse
        agent_resp = AgentResponse(
            agent_name="TestAgent",
            message="This is a test response",
            actions=[{"type": "navigate", "target": "/results"}],
            metadata={"test": True}
        )
        print(f"  AgentResponse created: agent={agent_resp.agent_name}")
        print(f"  AgentResponse success: {agent_resp.success}")
        
        # Test serialization
        json_str = agent_resp.model_dump_json()
        print(f"  AgentResponse JSON length: {len(json_str)} chars")
        
        print("\n✅ Common schemas working")
        return True
        
    except ImportError as e:
        print(f"\n❌ Common schemas import failed: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Common schemas error: {e}")
        return False


def test_chat_schemas():
    """Test Step 3: schemas/chat.py"""
    print("\n" + "=" * 50)
    print("Step 3: Testing schemas/chat.py")
    print("=" * 50)
    
    try:
        from backend.schemas.chat import ChatRequest, ChatResponse
        from backend.schemas.common import PageContext
        
        # Test ChatRequest
        page_ctx = PageContext(
            route="/literature",
            workspace_id="ws_test123",
            user_id="user_abc"
        )
        
        chat_req = ChatRequest(
            message="Find papers on CRISPR",
            page_context=page_ctx,
            stream=False
        )
        print(f"  ChatRequest created: message='{chat_req.message[:30]}...'")
        print(f"  ChatRequest stream: {chat_req.stream}")
        
        # Test ChatResponse with auto-generated timestamp
        chat_resp = ChatResponse(
            response="Found 5 papers on CRISPR gene editing.",
            agent_used="LiteratureAgent",
            intent="literature_search",
            metadata={"papers_found": 5}
        )
        print(f"  ChatResponse created: agent={chat_resp.agent_used}")
        print(f"  ChatResponse intent: {chat_resp.intent}")
        
        # Verify timestamp is datetime type
        if isinstance(chat_resp.timestamp, datetime):
            print(f"  ChatResponse timestamp: {chat_resp.timestamp.isoformat()}")
            print(f"  Timestamp type: datetime ✓")
        else:
            print(f"  ❌ Timestamp is not datetime: {type(chat_resp.timestamp)}")
            return False
        
        # Test serialization
        json_str = chat_resp.model_dump_json()
        print(f"  ChatResponse JSON length: {len(json_str)} chars")
        
        print("\n✅ Chat schemas working")
        return True
        
    except ImportError as e:
        print(f"\n❌ Chat schemas import failed: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Chat schemas error: {e}")
        return False


def main():
    """Run all verification tests."""
    print("\n" + "=" * 50)
    print("  NEXUS WORKSPACE BACKEND - FOUNDATION VERIFICATION")
    print("=" * 50)
    
    results = []
    
    # Run tests
    results.append(("Config", test_config()))
    results.append(("Common Schemas", test_common_schemas()))
    results.append(("Chat Schemas", test_chat_schemas()))
    
    # Summary
    print("\n" + "=" * 50)
    print("  SUMMARY")
    print("=" * 50)
    
    all_passed = True
    for name, passed in results:
        status = "✅" if passed else "❌"
        print(f"  {status} {name}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print("✅ All foundation verified - ready for agents!")
        return 0
    else:
        print("❌ Some tests failed - fix issues before proceeding")
        return 1


if __name__ == "__main__":
    sys.exit(main())
