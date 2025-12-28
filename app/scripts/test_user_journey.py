#!/usr/bin/env python3
"""Test user journey for all routes.

Tests each route in sequence to verify end-to-end functionality.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import httpx


BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"


async def test_health():
    """Step 0: Sanity check - Health endpoint."""
    print("=" * 80)
    print("STEP 0: Health Check")
    print("=" * 80)
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Test /health
        print("\n📡 Testing GET /health...")
        try:
            response = await client.get(f"{BASE_URL}/health")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Health check passed!")
                print(f"   Response: {data}")
                return True
            else:
                print(f"   ❌ Health check failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
        except httpx.ConnectError:
            print(f"   ❌ Cannot connect to server at {BASE_URL}")
            print(f"   💡 Make sure the server is running: make run")
            return False
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
        
        # Test /v1/version
        print("\n📡 Testing GET /api/v1/version...")
        try:
            response = await client.get(f"{API_BASE}/version")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Version endpoint passed!")
                print(f"   Response: {data}")
                return True
            else:
                print(f"   ❌ Version endpoint failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False


async def test_workspaces():
    """Step 1: Workspace CRUD."""
    print("\n" + "=" * 80)
    print("STEP 1: Workspace CRUD")
    print("=" * 80)
    
    import uuid
    owner_user_id = str(uuid.uuid4())
    workspace_id = None
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Create workspace
        print("\n📦 Testing POST /v1/workspaces...")
        try:
            response = await client.post(
                f"{API_BASE}/workspaces",
                json={"name": "Test Workspace", "plan_tier": "free"},
                params={"owner_user_id": owner_user_id},
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 201:
                data = response.json()
                workspace_id = data["id"]
                print(f"   ✅ Workspace created: {workspace_id}")
                return workspace_id, owner_user_id
            else:
                print(f"   ❌ Failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return None, None
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return None, None


async def test_documents(workspace_id, user_id):
    """Step 2: Document operations."""
    print("\n" + "=" * 80)
    print("STEP 2: Document Operations")
    print("=" * 80)
    
    document_id = None
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Create document
        print("\n📄 Testing POST /v1/workspaces/{workspace_id}/documents...")
        try:
            response = await client.post(
                f"{API_BASE}/workspaces/{workspace_id}/documents",
                json={
                    "workspace_id": workspace_id,
                    "user_id": user_id,
                    "title": "Test Document",
                    "doc_type": "text",
                    "content": "This is a test document for MentraFlow.",
                },
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 201:
                data = response.json()
                document_id = data["id"]
                print(f"   ✅ Document created: {document_id}")
                print(f"   Status: {data.get('status', 'unknown')}")
            else:
                print(f"   ❌ Failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return None
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return None
        
        # Get document
        print(f"\n📖 Testing GET /v1/documents/{document_id}...")
        try:
            response = await client.get(f"{API_BASE}/documents/{document_id}")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Document retrieved")
                print(f"   Summary: {data.get('summary_text', 'Not yet generated')[:50]}...")
            else:
                print(f"   ❌ Failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        return document_id


async def run_all_tests():
    """Run all user journey tests."""
    print("\n🚀 Starting User Journey Tests")
    print("=" * 80)
    
    # Step 0: Health check
    health_ok = await test_health()
    if not health_ok:
        print("\n❌ Health check failed. Please start the server first: make run")
        return 1
    
    # Step 1: Workspaces
    workspace_id, user_id = await test_workspaces()
    if not workspace_id:
        print("\n❌ Workspace creation failed")
        return 1
    
    # Step 2: Documents
    document_id = await test_documents(workspace_id, user_id)
    if not document_id:
        print("\n❌ Document creation failed")
        return 1
    
    print("\n" + "=" * 80)
    print("✅ USER JOURNEY TESTS COMPLETE")
    print("=" * 80)
    print(f"\nCreated resources:")
    print(f"  - Workspace ID: {workspace_id}")
    print(f"  - User ID: {user_id}")
    print(f"  - Document ID: {document_id}")
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(run_all_tests())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

