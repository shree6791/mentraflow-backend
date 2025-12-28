#!/usr/bin/env python3
"""End-to-end development flow runner.

Runs the happy path: create workspace -> upload doc -> ingest -> get doc (summary) -> chat -> flashcards -> due -> review.
"""
import asyncio
import sys
import uuid
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import httpx


BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"


async def run_devflow():
    """Run the complete development flow."""
    print("=" * 80)
    print("MENTRAFLOW DEVFLOW RUNNER")
    print("=" * 80)
    print()
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Step 1: Create workspace
        print("📦 Step 1: Creating workspace...")
        workspace_data = {
            "name": "Test Workspace",
            "plan_tier": "free",
        }
        owner_user_id = str(uuid.uuid4())  # Generate test user ID
        
        try:
            response = await client.post(
                f"{API_BASE}/workspaces?owner_user_id={owner_user_id}",
                json=workspace_data,
            )
            response.raise_for_status()
            workspace = response.json()
            workspace_id = workspace["id"]
            print(f"✅ Created workspace: {workspace_id}")
        except Exception as e:
            print(f"❌ Failed to create workspace: {e}")
            return 1
        
        # Step 2: Create document
        print("\n📄 Step 2: Creating document...")
        document_data = {
            "workspace_id": workspace_id,
            "user_id": owner_user_id,
            "title": "Test Document - Machine Learning Basics",
            "doc_type": "text",
            "content": """
Machine learning is a subset of artificial intelligence that focuses on algorithms that can learn from data.
It enables computers to improve their performance on a task through experience without being explicitly programmed.

Key concepts:
- Supervised learning: Learning from labeled examples
- Unsupervised learning: Finding patterns in unlabeled data
- Reinforcement learning: Learning through trial and error with rewards

Neural networks are a popular approach, inspired by biological neurons. They consist of layers of interconnected nodes that process information.

Deep learning uses neural networks with many layers to learn complex patterns in data.
            """.strip(),
        }
        
        try:
            response = await client.post(
                f"{API_BASE}/workspaces/{workspace_id}/documents",
                json=document_data,
            )
            response.raise_for_status()
            document = response.json()
            document_id = document["id"]
            print(f"✅ Created document: {document_id}")
            print(f"   Status: {document.get('status', 'unknown')}")
        except Exception as e:
            print(f"❌ Failed to create document: {e}")
            return 1
        
        # Step 3: Wait for auto-ingest (if enabled) or manually ingest
        print("\n🔄 Step 3: Ingesting document...")
        ingest_data = {
            "workspace_id": workspace_id,
            "user_id": owner_user_id,
        }
        
        try:
            response = await client.post(
                f"{API_BASE}/documents/{document_id}/ingest?async=false",
                json=ingest_data,
            )
            response.raise_for_status()
            ingest_result = response.json()
            print(f"✅ Ingestion complete:")
            print(f"   Chunks created: {ingest_result.get('chunks_created', 0)}")
            print(f"   Embeddings created: {ingest_result.get('embeddings_created', 0)}")
        except Exception as e:
            print(f"⚠️  Ingestion may have failed or is running async: {e}")
            print("   Continuing with flow...")
        
        # Step 4: Get document (with summary)
        print("\n📖 Step 4: Getting document with summary...")
        try:
            response = await client.get(f"{API_BASE}/documents/{document_id}")
            response.raise_for_status()
            document = response.json()
            print(f"✅ Document retrieved:")
            print(f"   Status: {document.get('status', 'unknown')}")
            summary = document.get("summary_text")
            if summary:
                print(f"   Summary: {summary[:200]}...")
            else:
                print("   Summary: Not yet generated")
        except Exception as e:
            print(f"❌ Failed to get document: {e}")
            return 1
        
        # Step 5: Chat with document
        print("\n💬 Step 5: Chatting with document...")
        chat_data = {
            "workspace_id": workspace_id,
            "user_id": owner_user_id,
            "message": "What is machine learning?",
            "document_id": document_id,
        }
        
        try:
            response = await client.post(f"{API_BASE}/chat", json=chat_data)
            response.raise_for_status()
            chat_result = response.json()
            print(f"✅ Chat response:")
            print(f"   Answer: {chat_result.get('content', '')[:200]}...")
            citations = chat_result.get("metadata", {}).get("citations", [])
            print(f"   Citations: {len(citations)} chunks referenced")
        except Exception as e:
            print(f"⚠️  Chat failed: {e}")
            print("   Continuing with flow...")
        
        # Step 6: Generate flashcards
        print("\n🎴 Step 6: Generating flashcards...")
        flashcard_data = {
            "workspace_id": workspace_id,
            "user_id": owner_user_id,
            "mode": "key_terms",
        }
        
        try:
            response = await client.post(
                f"{API_BASE}/documents/{document_id}/flashcards?async=false",
                json=flashcard_data,
            )
            response.raise_for_status()
            flashcard_result = response.json()
            print(f"✅ Flashcards generated:")
            print(f"   Created: {flashcard_result.get('flashcards_created', 0)}")
            preview = flashcard_result.get("preview", [])
            if preview:
                print(f"   Preview: {preview[0].get('front', 'N/A')[:50]}...")
        except Exception as e:
            print(f"⚠️  Flashcard generation failed: {e}")
            print("   Continuing with flow...")
        
        # Step 7: Get due flashcards
        print("\n📅 Step 7: Getting due flashcards...")
        try:
            response = await client.get(
                f"{API_BASE}/flashcards/due?workspace_id={workspace_id}&user_id={owner_user_id}&limit=5"
            )
            response.raise_for_status()
            due_flashcards = response.json()
            print(f"✅ Found {len(due_flashcards)} due flashcards")
            if due_flashcards:
                print(f"   First card: {due_flashcards[0].get('front', 'N/A')[:50]}...")
        except Exception as e:
            print(f"⚠️  Failed to get due flashcards: {e}")
            print("   Continuing with flow...")
        
        # Step 8: Review a flashcard (if available)
        if due_flashcards:
            print("\n⭐ Step 8: Reviewing a flashcard...")
            flashcard_id = due_flashcards[0]["id"]
            review_data = {
                "user_id": owner_user_id,
                "workspace_id": workspace_id,
                "grade": 3,  # Good
                "response_time_ms": 2000,
            }
            
            try:
                response = await client.post(
                    f"{API_BASE}/flashcards/{flashcard_id}/review",
                    json=review_data,
                )
                response.raise_for_status()
                review_result = response.json()
                print(f"✅ Review recorded:")
                print(f"   Next due: {review_result.get('next_review_due', 'N/A')}")
                print(f"   Interval: {review_result.get('interval_days', 'N/A')} days")
            except Exception as e:
                print(f"⚠️  Review failed: {e}")
        
        print("\n" + "=" * 80)
        print("✅ DEVFLOW COMPLETE")
        print("=" * 80)
        return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(run_devflow())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Flow interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

