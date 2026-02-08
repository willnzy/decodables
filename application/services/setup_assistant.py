#!/usr/bin/env python3
"""
Setup script for OpenAI Assistant with RAG (Retrieval-Augmented Generation)

This script creates/updates:
1. Uploads knowledge_base.md to OpenAI Files
2. Creates a Vector Store for file search
3. Creates/updates the Support Assistant

Run this script once to set up, or again to update the knowledge base.

Usage:
    python setup_assistant.py

Environment variables required:
    OPENAI_API_KEY - Your OpenAI API key (can be in .env file)
"""

import os
import sys

# Load .env file if exists
from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI

# Configuration
ASSISTANT_NAME = "Make Decodables Support Assistant"
KNOWLEDGE_BASE_PATH = os.path.join(os.path.dirname(__file__), "knowledge_base.md")
VECTOR_STORE_NAME = "Make Decodables Knowledge Base"

# Assistant instructions (system prompt)
ASSISTANT_INSTRUCTIONS = """You are a friendly and helpful customer support assistant for Make Decodables.

Your role is to:
1. Answer questions about Make Decodables product features, pricing, and usage
2. Help users troubleshoot common issues
3. Guide users on how to use different features
4. Be concise, friendly, and professional

Important guidelines:
- Keep responses short and helpful (2-4 sentences when possible)
- If you're not sure about something, suggest the user contact human support via WhatsApp (+1 725 290 0525) or email (info@foliaz.com)
- Always be encouraging and positive
- Use simple language suitable for teachers and parents
- If a question is outside the scope of Make Decodables, politely redirect
- When answering, reference the knowledge base but don't quote it verbatim
- If user uploads an image, describe what you see and help with their question

Remember: Be helpful, concise, and friendly!"""


def main():
    # Initialize OpenAI client
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        sys.exit(1)
    
    client = OpenAI(api_key=api_key)
    
    print("🚀 Setting up Make Decodables Support Assistant...")
    print()
    
    # Step 1: Upload knowledge base file
    print("📄 Step 1: Uploading knowledge base file...")
    if not os.path.exists(KNOWLEDGE_BASE_PATH):
        print(f"❌ Error: Knowledge base file not found: {KNOWLEDGE_BASE_PATH}")
        sys.exit(1)
    
    with open(KNOWLEDGE_BASE_PATH, "rb") as f:
        file = client.files.create(
            file=f,
            purpose="assistants"
        )
    print(f"   ✅ File uploaded: {file.id}")
    
    # Step 2: Create Vector Store using the REST API directly
    print()
    print("🗄️ Step 2: Creating Vector Store...")
    import httpx
    
    # Create vector store via REST API
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "OpenAI-Beta": "assistants=v2"
    }
    
    # Create vector store
    vs_response = httpx.post(
        "https://api.openai.com/v1/vector_stores",
        headers=headers,
        json={
            "name": VECTOR_STORE_NAME,
            "file_ids": [file.id]
        },
        timeout=60
    )
    
    if vs_response.status_code != 200:
        print(f"❌ Error creating vector store: {vs_response.text}")
        sys.exit(1)
    
    vector_store = vs_response.json()
    vector_store_id = vector_store["id"]
    print(f"   ✅ Vector Store created: {vector_store_id}")
    
    # Wait for file to be processed
    print("   ⏳ Processing file...")
    import time
    while True:
        vs_status = httpx.get(
            f"https://api.openai.com/v1/vector_stores/{vector_store_id}",
            headers=headers,
            timeout=30
        ).json()
        if vs_status.get("file_counts", {}).get("completed", 0) >= vs_status.get("file_counts", {}).get("total", 1):
            break
        time.sleep(1)
    print(f"   ✅ File processed successfully")
    
    # Step 3: Create Assistant
    print()
    print("🤖 Step 3: Creating Assistant...")
    assistant = client.beta.assistants.create(
        name=ASSISTANT_NAME,
        instructions=ASSISTANT_INSTRUCTIONS,
        model="gpt-4o-mini",  # Cost-effective, switch to gpt-4o for better quality
        tools=[{"type": "file_search"}],
        tool_resources={
            "file_search": {
                "vector_store_ids": [vector_store_id]
            }
        }
    )
    print(f"   ✅ Assistant created: {assistant.id}")
    
    # Summary
    print()
    print("=" * 60)
    print("✅ Setup Complete!")
    print("=" * 60)
    print()
    print("Add these to your environment variables:")
    print()
    print(f"   OPENAI_ASSISTANT_ID={assistant.id}")
    print(f"   OPENAI_VECTOR_STORE_ID={vector_store_id}")
    print()
    print("For Railway/Vercel, add these in the dashboard.")
    print()
    print("=" * 60)
    
    # Save to .env.assistant file for reference
    env_file = os.path.join(os.path.dirname(__file__), ".env.assistant")
    with open(env_file, "w") as f:
        f.write(f"# Generated by setup_assistant.py\n")
        f.write(f"OPENAI_ASSISTANT_ID={assistant.id}\n")
        f.write(f"OPENAI_VECTOR_STORE_ID={vector_store_id}\n")
        f.write(f"# File ID (for reference): {file.id}\n")
    print(f"💾 Saved to {env_file} for reference")


if __name__ == "__main__":
    main()
