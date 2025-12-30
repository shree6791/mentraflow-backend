#!/usr/bin/env python3
"""Debug script to check flashcards in database."""
import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import select, text
from app.infrastructure.database import AsyncSessionLocal
from app.models.flashcard import Flashcard
from app.models.document import Document
from app.models.user import User
from app.models.agent_run import AgentRun


async def debug_flashcards(workspace_id: str, document_id: str):
    """Debug flashcards query."""
    async with AsyncSessionLocal() as db:
        # Ensure search_path is set to mentraflow schema
        await db.execute(text("SET search_path TO mentraflow, public"))
        
        workspace_uuid = workspace_id
        document_uuid = document_id
        
        print(f"\n🔍 Debugging flashcards for:")
        print(f"   Workspace ID: {workspace_uuid}")
        print(f"   Document ID: {document_uuid}\n")
        
        # 1. Check document
        doc_stmt = select(Document).where(Document.id == document_uuid)
        doc_result = await db.execute(doc_stmt)
        document = doc_result.scalar_one_or_none()
        
        if not document:
            print(f"❌ Document {document_uuid} not found!")
            return
        
        print(f"✅ Document found:")
        print(f"   - Document ID: {document.id}")
        print(f"   - Workspace ID: {document.workspace_id}")
        print(f"   - User ID (owner): {document.user_id}")
        print(f"   - Title: {document.title or 'N/A'}\n")
        
        # 2. Check all flashcards for this document (any user)
        all_flashcards_stmt = select(Flashcard).where(
            Flashcard.document_id == document_uuid
        )
        all_result = await db.execute(all_flashcards_stmt)
        all_flashcards = list(all_result.scalars().all())
        
        print(f"📊 All flashcards for document (any user): {len(all_flashcards)}")
        if all_flashcards:
            for fc in all_flashcards:
                print(f"   - Flashcard ID: {fc.id}")
                print(f"     User ID: {fc.user_id}")
                print(f"     Workspace ID: {fc.workspace_id}")
                print(f"     Card Type: {fc.card_type}")
                print(f"     Front: {fc.front[:50] if fc.front else 'N/A'}...")
                print()
        
        # 3. Check flashcards for document owner
        owner_flashcards_stmt = select(Flashcard).where(
            Flashcard.document_id == document_uuid,
            Flashcard.user_id == document.user_id
        )
        owner_result = await db.execute(owner_flashcards_stmt)
        owner_flashcards = list(owner_result.scalars().all())
        
        print(f"📊 Flashcards for document owner (user_id={document.user_id}): {len(owner_flashcards)}\n")
        
        # 4. Check flashcards by workspace (any user)
        workspace_flashcards_stmt = select(Flashcard).where(
            Flashcard.workspace_id == workspace_uuid
        )
        workspace_result = await db.execute(workspace_flashcards_stmt)
        workspace_flashcards = list(workspace_result.scalars().all())
        
        print(f"📊 All flashcards in workspace (any user): {len(workspace_flashcards)}")
        if workspace_flashcards:
            user_ids = set(fc.user_id for fc in workspace_flashcards)
            print(f"   User IDs with flashcards: {user_ids}")
            print(f"   Flashcard details:")
            for fc in workspace_flashcards[:10]:  # Show first 10
                print(f"     - ID: {fc.id}")
                print(f"       Document ID: {fc.document_id or 'NULL'}")
                print(f"       User ID: {fc.user_id}")
                print(f"       Card Type: {fc.card_type}")
                print(f"       Front: {fc.front[:50] if fc.front else 'N/A'}...")
                print()
            if len(workspace_flashcards) > 10:
                print(f"     ... and {len(workspace_flashcards) - 10} more\n")
        
        # 5. Check what the API query would return (simulating with document owner)
        api_query_stmt = select(Flashcard).where(
            Flashcard.workspace_id == workspace_uuid,
            Flashcard.user_id == document.user_id,
            Flashcard.document_id == document_uuid
        )
        api_result = await db.execute(api_query_stmt)
        api_flashcards = list(api_result.scalars().all())
        
        print(f"📊 API query result (workspace_id={workspace_uuid}, user_id={document.user_id}, document_id={document_uuid}): {len(api_flashcards)}\n")
        
        # 6. Show user info
        user_stmt = select(User).where(User.id == document.user_id)
        user_result = await db.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        
        if user:
            print(f"👤 Document owner:")
            print(f"   - User ID: {user.id}")
            print(f"   - Username: {user.username}")
            print(f"   - Email: {user.email}\n")
        
        # 7. Check agent runs for this document to see if flashcard generation ran
        from app.models.agent_run import AgentRun
        # AgentRun doesn't have document_id field, check all runs for this workspace/user
        # and filter by document_id in input JSONB
        all_runs_stmt = select(AgentRun).where(
            AgentRun.workspace_id == workspace_uuid,
            AgentRun.user_id == document.user_id
        ).order_by(AgentRun.started_at.desc()).limit(20)
        all_runs_result = await db.execute(all_runs_stmt)
        all_runs = list(all_runs_result.scalars().all())
        
        # Filter runs for this document (document_id is in input JSONB)
        runs_for_doc = []
        for run in all_runs:
            if run.input and isinstance(run.input, dict):
                run_doc_id = run.input.get("document_id") or run.input.get("source_document_id")
                if run_doc_id and str(run_doc_id) == str(document_uuid):
                    runs_for_doc.append(run)
        
        print(f"📊 Agent runs for document {document_uuid}: {len(runs_for_doc)}")
        if runs_for_doc:
            for run in runs_for_doc[:5]:
                print(f"   - Agent: {run.agent_name}, Status: {run.status}, Started: {run.started_at}")
                if run.steps:
                    flashcard_steps = [s for s in run.steps if 'flashcard' in s.get('step_name', '').lower()]
                    if flashcard_steps:
                        for step in flashcard_steps:
                            print(f"     * {step.get('step_name')}: {step.get('step_status')}")
        else:
            print("   ⚠️  No agent runs found for this document")
            print(f"   (Checked {len(all_runs)} total runs for workspace/user)")
        print()
        
        print("\n💡 Summary:")
        print(f"   - Document {document_uuid} ('{document.title}'):")
        print(f"     * Total flashcards (any user): {len(all_flashcards)}")
        print(f"     * Flashcards for owner (user_id={document.user_id}): {len(owner_flashcards)}")
        print(f"     * API query would return (as owner): {len(api_flashcards)} flashcards")
        
        if len(all_flashcards) == 0:
            if len(workspace_flashcards) > 0:
                doc_ids = set(str(fc.document_id) for fc in workspace_flashcards if fc.document_id)
                print(f"\n   ⚠️  No flashcards for this document, but {len(workspace_flashcards)} flashcards exist in workspace")
                print(f"   - Flashcards belong to document(s): {', '.join(doc_ids)}")
                if str(document_uuid) not in doc_ids:
                    print(f"   - You may be querying for the wrong document_id")
            else:
                print(f"\n   ⚠️  No flashcards found in workspace")
                print("   - Check if document ingestion completed")
                print("   - Verify that auto_flashcards_after_ingest is enabled in user preferences")
        else:
            print(f"\n   ✅ Flashcards exist and are correctly linked to this document")
            if len(api_flashcards) != len(owner_flashcards):
                print(f"   ⚠️  API query simulation shows {len(api_flashcards)} flashcards, but owner has {len(owner_flashcards)}")
            print(f"\n   📝 To see these flashcards via API:")
            print(f"      - You need a valid JWT token for user_id={document.user_id}")
            print(f"      - If user signed in via Google, use GOOGLE_ID_TOKEN environment variable")
            print(f"      - Or use password login if user has a password set")
        print()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python debug_flashcards.py <workspace_id> <document_id>")
        sys.exit(1)
    
    workspace_id = sys.argv[1]
    document_id = sys.argv[2]
    
    asyncio.run(debug_flashcards(workspace_id, document_id))

