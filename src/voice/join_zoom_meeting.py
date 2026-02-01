#!/usr/bin/env python3
"""Standalone Zoom Bot - Run this script to join a Zoom meeting.

Usage:
    python -m src.voice.join_zoom_meeting --url "https://zoom.us/j/123456789?pwd=xxx" --name "Onboarding Bot"
"""

import argparse
import asyncio
import base64
import re
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(__file__).rsplit("/src/", 1)[0])

import httpx


async def synthesize_speech(text: str, api_key: str) -> bytes:
    """Generate speech audio using ElevenLabs."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.elevenlabs.io/v1/text-to-speech/21m00Tcm4TlvDq8ikWAM",
            headers={
                "xi-api-key": api_key,
                "Content-Type": "application/json",
            },
            json={
                "text": text,
                "model_id": "eleven_turbo_v2_5",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                },
            },
        )
        if response.status_code == 200:
            return response.content
        return b""


async def query_knowledge_base(query: str, api_base: str = "http://localhost:8000") -> dict:
    """Query the knowledge base for an answer."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Create a session first
        session_resp = await client.post(
            f"{api_base}/api/v1/voice/agent/sessions",
            json={
                "user_id": "zoom_standalone",
                "user_name": "Zoom Bot",
                "user_department": "Engineering",
            },
        )
        
        if session_resp.status_code != 200:
            return {"text": "I'm sorry, I couldn't connect to the knowledge base.", "sources": []}
        
        session = session_resp.json()
        session_id = session["session_id"]
        
        # Query
        query_resp = await client.post(
            f"{api_base}/api/v1/voice/agent/sessions/{session_id}/query",
            json={"query": query, "include_audio": False},
        )
        
        if query_resp.status_code == 200:
            return query_resp.json()
        
        return {"text": "I couldn't find an answer to that question.", "sources": []}


async def join_zoom_meeting(
    meeting_url: str,
    bot_name: str = "Onboarding Assistant",
    passcode: str | None = None,
    elevenlabs_key: str = "",
):
    """Join a Zoom meeting and interact with voice."""
    from playwright.async_api import async_playwright

    # Parse meeting URL
    match = re.search(r'/j/(\d+)', meeting_url)
    meeting_id = match.group(1) if match else ""
    
    if not passcode:
        pwd_match = re.search(r'pwd=([^&\s]+)', meeting_url)
        passcode = pwd_match.group(1) if pwd_match else None

    print(f"🤖 Starting Zoom Bot: {bot_name}")
    print(f"📍 Meeting ID: {meeting_id}")
    print(f"🔑 Passcode: {'Yes' if passcode else 'No'}")
    print()

    async with async_playwright() as playwright:
        print("🌐 Launching browser...")
        
        browser = await playwright.chromium.launch(
            headless=False,
            args=[
                "--use-fake-ui-for-media-stream",
                "--use-fake-device-for-media-stream",
                "--auto-accept-camera-and-microphone-capture",
            ]
        )

        context = await browser.new_context(
            permissions=["microphone", "camera"],
            viewport={"width": 1280, "height": 720},
        )

        page = await context.new_page()

        # Navigate to Zoom web client
        web_url = meeting_url.replace("/j/", "/wc/join/")
        if "?" in web_url:
            web_url = web_url.split("?")[0]
        
        print(f"📱 Navigating to: {web_url}")
        await page.goto(web_url)
        await asyncio.sleep(3)

        # Fill name
        try:
            print("✏️ Entering bot name...")
            name_input = await page.wait_for_selector(
                '#inputname, input[placeholder*="name" i], input[name="name"]',
                timeout=15000
            )
            if name_input:
                await name_input.fill(bot_name)
        except Exception as e:
            print(f"⚠️ Could not find name input: {e}")

        # Fill passcode if needed
        if passcode:
            try:
                print("🔐 Entering passcode...")
                pwd_input = await page.wait_for_selector(
                    '#inputpasscode, input[type="password"], input[placeholder*="password" i]',
                    timeout=5000
                )
                if pwd_input:
                    await pwd_input.fill(passcode)
            except Exception:
                pass

        # Click join
        try:
            print("🚀 Clicking join button...")
            join_btn = await page.wait_for_selector(
                'button:has-text("Join"), #joinBtn, .zm-btn--primary',
                timeout=5000
            )
            if join_btn:
                await join_btn.click()
        except Exception:
            pass

        await asyncio.sleep(5)

        # Try to join audio
        try:
            print("🔊 Joining audio...")
            audio_btn = await page.wait_for_selector(
                'button:has-text("Join Audio"), button:has-text("Computer Audio")',
                timeout=10000
            )
            if audio_btn:
                await audio_btn.click()
        except Exception:
            pass

        print()
        print("=" * 50)
        print("✅ BOT IS IN THE MEETING!")
        print("=" * 50)
        print()
        print("Commands:")
        print("  /say <text>  - Make the bot speak")
        print("  /ask <query> - Ask the knowledge base and speak the answer")
        print("  /quit        - Leave the meeting")
        print()

        # Interactive loop
        while True:
            try:
                command = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: input("Enter command: ")
                )
                
                if command.startswith("/quit"):
                    print("👋 Leaving meeting...")
                    break
                
                elif command.startswith("/say "):
                    text = command[5:]
                    print(f"🗣️ Speaking: {text}")
                    
                    if elevenlabs_key:
                        audio = await synthesize_speech(text, elevenlabs_key)
                        if audio:
                            audio_b64 = base64.b64encode(audio).decode()
                            await page.evaluate(f"""
                                (async () => {{
                                    const audio = new Audio('data:audio/mp3;base64,{audio_b64}');
                                    audio.volume = 1.0;
                                    await audio.play();
                                }})();
                            """)
                            print("✅ Audio played")
                        else:
                            print("❌ Failed to generate audio")
                    else:
                        print("❌ No ElevenLabs API key configured")
                
                elif command.startswith("/ask "):
                    query = command[5:]
                    print(f"❓ Asking: {query}")
                    
                    result = await query_knowledge_base(query)
                    answer = result.get("text", "I don't know.")
                    print(f"💡 Answer: {answer}")
                    
                    if elevenlabs_key:
                        audio = await synthesize_speech(answer, elevenlabs_key)
                        if audio:
                            audio_b64 = base64.b64encode(audio).decode()
                            await page.evaluate(f"""
                                (async () => {{
                                    const audio = new Audio('data:audio/mp3;base64,{audio_b64}');
                                    audio.volume = 1.0;
                                    await audio.play();
                                }})();
                            """)
                            print("✅ Answer spoken")
                
                else:
                    print("Unknown command. Use /say, /ask, or /quit")
                    
            except KeyboardInterrupt:
                print("\n👋 Leaving meeting...")
                break
            except Exception as e:
                print(f"Error: {e}")

        await browser.close()
        print("✅ Bot has left the meeting")


def main():
    parser = argparse.ArgumentParser(description="Zoom Onboarding Bot")
    parser.add_argument("--url", required=True, help="Zoom meeting URL")
    parser.add_argument("--name", default="Onboarding Assistant", help="Bot display name")
    parser.add_argument("--passcode", help="Meeting passcode (if not in URL)")
    parser.add_argument("--elevenlabs-key", default="sk_d7ca2cd289670ae397f0f0ac7a2e70d3b2dc85d963bed00f", help="ElevenLabs API key")
    
    args = parser.parse_args()
    
    asyncio.run(join_zoom_meeting(
        meeting_url=args.url,
        bot_name=args.name,
        passcode=args.passcode,
        elevenlabs_key=args.elevenlabs_key,
    ))


if __name__ == "__main__":
    main()
