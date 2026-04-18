#!/usr/bin/env python3
"""
Test script to verify Server-Sent Events (SSE) streaming implementation.
Tests real-time token streaming, metadata collection, and timing.
"""

import asyncio
import json
import time
from typing import AsyncGenerator
import httpx
from datetime import datetime


async def test_streaming() -> None:
    """Test the streaming chat endpoint."""
    base_url = "http://raze_backend:8000"

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Step 1: Authenticate
        print("=" * 60)
        print("STEP 1: Authentication")
        print("=" * 60)

        auth_response = await client.post(
            f"{base_url}/api/v1/auth/login",
            json={"email": "admin@yourcompany.com", "password": "admin"}
        )

        if auth_response.status_code != 200:
            print(f"❌ Authentication failed: {auth_response.status_code}")
            print(f"Response: {auth_response.text[:200]}")
            return

        auth_data = auth_response.json()
        token = auth_data.get("access_token")
        print(f"✅ Authentication successful")
        print(f"   Token: {token[:20]}..." if token else "   No token received")

        # Step 2: Test streaming endpoint
        print("\n" + "=" * 60)
        print("STEP 2: Streaming Chat Test")
        print("=" * 60)

        headers = {"Authorization": f"Bearer {token}"}
        test_message = "Hello! What is your name and what can you help me with?"
        session_id = f"test-session-{int(time.time())}"

        print(f"Message: {test_message}")
        print(f"Session ID: {session_id}")
        print(f"Timestamp: {datetime.now().isoformat()}")

        stream_start = time.time()

        try:
            response = await client.post(
                f"{base_url}/api/v1/chat/stream",
                json={
                    "message": test_message,
                    "session_id": session_id,
                    "use_knowledge": True,
                },
                headers=headers
            )

            if response.status_code != 200:
                print(f"❌ Stream failed: {response.status_code}")
                print(f"Response: {response.text[:200]}")
                return

            print(f"\n✅ Stream started (HTTP {response.status_code})")

            # Step 3: Parse SSE stream
            print("\n" + "=" * 60)
            print("STEP 3: Receiving Stream Events")
            print("=" * 60)

            events_received = 0
            text_chunks = []
            metadata = {}
            first_token_time = None

            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    try:
                        event = json.loads(line[6:])
                        events_received += 1
                        event_type = event.get("event", "unknown")

                        if event_type == "start":
                            print(f"\n🟢 START event")
                            print(f"   Conversation ID: {str(event.get('conversation_id', ''))[:8]}...")
                            print(f"   Message ID: {str(event.get('message_id', ''))[:8]}...")

                        elif event_type == "delta":
                            if first_token_time is None:
                                first_token_time = time.time() - stream_start
                                print(f"\n🟡 FIRST TOKEN received in {first_token_time:.3f}s")

                            text = event.get("text", "")
                            text_chunks.append(text)
                            # Print preview of text chunks
                            if len(text_chunks) <= 5:
                                preview = text[:50].replace('\n', '\\n')
                                print(f"   [{len(text_chunks)}] Delta: {preview}...")

                        elif event_type == "done":
                            print(f"\n🔴 DONE event")
                            print(f"   Tokens used: {event.get('tokens_used', 0)}")
                            print(f"   Cost: ${event.get('cost_usd', 0):.6f}")
                            print(f"   Latency: {event.get('latency_ms', 0)}ms")
                            print(f"   Model: {event.get('model_used', 'unknown')}")
                            metadata = {k: v for k, v in event.items()
                                       if k not in ["event", "message_id", "conversation_id"]}

                    except json.JSONDecodeError:
                        pass  # Skip invalid JSON lines

            total_time = time.time() - stream_start
            full_text = "".join(text_chunks)

            # Step 4: Summary
            print("\n" + "=" * 60)
            print("STEP 4: Stream Summary")
            print("=" * 60)

            print(f"\n📊 Statistics:")
            print(f"   Total events: {events_received}")
            print(f"   Text chunks: {len(text_chunks)}")
            print(f"   Response length: {len(full_text)} characters")
            print(f"   First token latency: {first_token_time:.3f}s" if first_token_time else "   First token: Not received")
            print(f"   Total streaming time: {total_time:.3f}s")
            print(f"   Tokens/second: {metadata.get('tokens_used', 0) / total_time:.1f}" if total_time > 0 else "   N/A")

            print(f"\n💬 Response Preview:")
            preview = full_text[:200].replace('\n', ' ')
            print(f"   {preview}...")

            # Step 5: Test conversations endpoint
            print("\n" + "=" * 60)
            print("STEP 5: Verify Conversation was Saved")
            print("=" * 60)

            conv_response = await client.get(
                f"{base_url}/api/v1/chat/conversations?page=1&page_size=5",
                headers=headers
            )

            if conv_response.status_code == 200:
                data = conv_response.json()
                print(f"✅ Conversations endpoint working")
                print(f"   Total conversations: {data.get('total', 0)}")

                if data.get('items'):
                    # Look for our test conversation
                    for conv in data['items']:
                        if test_message[:10] in (conv.get('title') or ''):
                            print(f"✅ Test conversation found!")
                            print(f"   Title: {conv.get('title', 'Untitled')}")
                            print(f"   Messages: {conv.get('message_count', 0)}")
                            print(f"   Created: {conv.get('created_at', 'N/A')}")
                            break
            else:
                print(f"❌ Conversations endpoint failed: {conv_response.status_code}")

        except Exception as e:
            print(f"❌ Error during streaming: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    print("🚀 RAZE Streaming Implementation Test\n")
    asyncio.run(test_streaming())
