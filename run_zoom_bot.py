#!/usr/bin/env python3
"""Standalone Zoom Bot Runner.

Run this script directly to have the onboarding assistant join a Zoom meeting.
The browser will open visibly so you can see the bot join.

Usage:
    python run_zoom_bot.py

The bot will:
1. Open a browser and join the Zoom meeting
2. Listen for questions (you can type them to simulate speech)
3. Query the knowledge base for answers
4. Generate spoken responses using ElevenLabs

Environment variables needed:
- ELEVENLABS_API_KEY (for TTS)
- DEEPGRAM_API_KEY (for STT - optional)
"""

import asyncio
import base64
import os
import sys

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from playwright.async_api import async_playwright


# Meeting details from the invitation
MEETING_URL = "https://illinois.zoom.us/j/83355084090?pwd=jYK59G4qn2bMKT4afWu0jiF6vPtbYa.1"
MEETING_PASSCODE = "845998"
BOT_NAME = "Onboarding Assistant"


async def query_knowledge_base(question: str) -> dict:
    """Query the backend knowledge base for an answer."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Use the voice agent to process the query
            response = await client.post(
                "http://localhost:8000/api/v1/voice/agent/sessions",
                json={
                    "user_id": "zoom_bot_user",
                    "user_name": "Zoom Participant",
                    "user_department": "Engineering",
                    "session_type": "zoom_meeting"
                }
            )

            if response.status_code != 200:
                print(f"Failed to create session: {response.text}")
                return {"text": "I'm sorry, I couldn't access the knowledge base.", "audio": None}

            session = response.json()
            session_id = session["session_id"]

            # Process the query
            query_response = await client.post(
                f"http://localhost:8000/api/v1/voice/agent/sessions/{session_id}/query",
                json={
                    "query": question,
                    "include_audio": False  # We'll generate audio separately
                }
            )

            if query_response.status_code == 200:
                result = query_response.json()
                return {
                    "text": result.get("text", "I don't have information on that."),
                    "sources": result.get("sources", [])
                }

            return {"text": "I couldn't process that question.", "sources": []}

    except Exception as e:
        print(f"Error querying knowledge base: {e}")
        return {"text": f"Sorry, I encountered an error: {str(e)}", "sources": []}


async def synthesize_speech(text: str) -> bytes | None:
    """Generate speech audio using ElevenLabs."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "http://localhost:8000/api/v1/voice/agent/synthesize",
                json={
                    "text": text,
                    "model_id": "eleven_turbo_v2_5"
                }
            )

            if response.status_code == 200:
                return response.content
    except Exception as e:
        print(f"Error synthesizing speech: {e}")

    return None


async def play_audio_in_browser(page, audio_bytes: bytes):
    """Play audio through the browser (into the Zoom meeting)."""
    if not audio_bytes:
        return

    audio_b64 = base64.b64encode(audio_bytes).decode()

    try:
        await page.evaluate(f"""
            (async () => {{
                const audio = new Audio('data:audio/mp3;base64,{audio_b64}');
                audio.volume = 1.0;
                await audio.play();
            }})();
        """)

        # Wait for audio to finish (estimate based on size)
        duration = len(audio_bytes) / 16000  # rough estimate
        await asyncio.sleep(duration + 1)

    except Exception as e:
        print(f"Error playing audio: {e}")


async def join_zoom_meeting():
    """Join the Zoom meeting and interact."""

    print("=" * 60)
    print("🤖 ZOOM ONBOARDING ASSISTANT BOT")
    print("=" * 60)
    print(f"Meeting URL: {MEETING_URL}")
    print(f"Bot Name: {BOT_NAME}")
    print()
    print("Starting browser...")

    async with async_playwright() as p:
        # Launch browser in headed mode so you can see it
        # Using Firefox as it's more stable on macOS
        browser = await p.firefox.launch(
            headless=False,
            firefox_user_prefs={
                "media.navigator.permission.disabled": True,
                "media.navigator.streams.fake": True,
            }
        )

        # Create context with permissions
        context = await browser.new_context(
            permissions=["microphone", "camera"],
            viewport={"width": 1280, "height": 720},
        )

        page = await context.new_page()

        # Convert to web client URL
        web_url = MEETING_URL.replace("/j/", "/wc/join/")
        if "?" in web_url:
            web_url = web_url.split("?")[0]

        print(f"Navigating to: {web_url}")
        await page.goto(web_url)
        await asyncio.sleep(3)

        # Fill in the name
        print("Looking for name input...")
        try:
            name_input = await page.wait_for_selector(
                '#inputname, input[placeholder*="name" i], input[name="name"]',
                timeout=15000
            )
            if name_input:
                await name_input.fill(BOT_NAME)
                print(f"✓ Filled bot name: {BOT_NAME}")
        except Exception as e:
            print(f"Could not find name input: {e}")

        # Fill password
        print("Looking for passcode input...")
        try:
            pwd_input = await page.wait_for_selector(
                '#inputpasscode, input[type="password"], input[placeholder*="password" i], input[placeholder*="passcode" i]',
                timeout=5000
            )
            if pwd_input:
                await pwd_input.fill(MEETING_PASSCODE)
                print("✓ Filled passcode")
        except Exception as e:
            print(f"Could not find password input: {e}")

        # Click join button
        print("Looking for join button...")
        try:
            join_btn = await page.wait_for_selector(
                'button:has-text("Join"), button:has-text("join"), #joinBtn, .zm-btn--primary',
                timeout=5000
            )
            if join_btn:
                await join_btn.click()
                print("✓ Clicked join button")
        except Exception as e:
            print(f"Could not find join button: {e}")

        await asyncio.sleep(5)

        # Try to join audio
        print("Looking for audio join button...")
        try:
            audio_btn = await page.wait_for_selector(
                'button:has-text("Join Audio"), button:has-text("Computer Audio")',
                timeout=10000
            )
            if audio_btn:
                await audio_btn.click()
                print("✓ Clicked audio join button")
        except Exception:
            pass

        print()
        print("=" * 60)
        print("🎤 BOT IS IN THE MEETING!")
        print("=" * 60)
        print()
        print("Commands:")
        print("  /say <text>   - Make the bot say something")
        print("  /ask <question> - Ask a question (queries knowledge base)")
        print("  /quit         - Leave the meeting")
        print()
        print("Or just type a question directly to query the knowledge base.")
        print()

        # Interactive loop
        while True:
            try:
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, input, "You: "
                )

                if not user_input:
                    continue

                if user_input.lower() == "/quit":
                    print("Leaving meeting...")
                    break

                if user_input.startswith("/say "):
                    text = user_input[5:]
                    print(f"🔊 Speaking: {text}")
                    audio = await synthesize_speech(text)
                    await play_audio_in_browser(page, audio)
                    continue

                if user_input.startswith("/ask "):
                    question = user_input[5:]
                else:
                    question = user_input

                print(f"🤔 Querying knowledge base: {question}")
                result = await query_knowledge_base(question)
                answer = result["text"]

                print(f"💡 Answer: {answer}")

                if result.get("sources"):
                    print(f"📚 Sources: {', '.join(s.get('title', 'Unknown') for s in result['sources'])}")

                print("🔊 Speaking response...")
                audio = await synthesize_speech(answer)
                await play_audio_in_browser(page, audio)

            except KeyboardInterrupt:
                print("\nInterrupted. Leaving meeting...")
                break
            except Exception as e:
                print(f"Error: {e}")

        # Cleanup
        await browser.close()
        print("✓ Browser closed. Goodbye!")


if __name__ == "__main__":
    asyncio.run(join_zoom_meeting())
