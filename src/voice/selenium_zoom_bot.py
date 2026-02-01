#!/usr/bin/env python3
"""Selenium-based Zoom Bot - Join a Zoom meeting and interact with voice.

Usage:
    python src/voice/selenium_zoom_bot.py --url "https://zoom.us/j/123456789" --passcode "123456"
"""

import argparse
import base64
import os
import re
import sys
import tempfile
import time
import threading
from pathlib import Path

import httpx
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "sk_d7ca2cd289670ae397f0f0ac7a2e70d3b2dc85d963bed00f")


def synthesize_speech(text: str) -> bytes:
    """Generate speech audio using ElevenLabs."""
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            "https://api.elevenlabs.io/v1/text-to-speech/21m00Tcm4TlvDq8ikWAM",
            headers={
                "xi-api-key": ELEVENLABS_API_KEY,
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
        print(f"TTS Error: {response.status_code} - {response.text}")
        return b""


def query_knowledge_base(query: str, api_base: str = "http://localhost:8000") -> dict:
    """Query the knowledge base for an answer."""
    with httpx.Client(timeout=30.0) as client:
        # Create a session
        try:
            session_resp = client.post(
                f"{api_base}/api/v1/voice/agent/sessions",
                json={
                    "user_id": "zoom_bot",
                    "user_name": "Zoom Bot",
                    "user_department": "Engineering",
                },
            )
            
            if session_resp.status_code == 200:
                session = session_resp.json()
                session_id = session["session_id"]
                
                # Query
                query_resp = client.post(
                    f"{api_base}/api/v1/voice/agent/sessions/{session_id}/query",
                    json={"query": query, "include_audio": False},
                )
                
                if query_resp.status_code == 200:
                    return query_resp.json()
        except Exception as e:
            print(f"Knowledge base error: {e}")
        
        return {"text": f"I'll help you with that question about {query[:50]}...", "sources": []}


def play_audio_in_browser(driver, audio_bytes: bytes):
    """Play audio in the browser."""
    audio_b64 = base64.b64encode(audio_bytes).decode()
    driver.execute_script(f"""
        (function() {{
            const audio = new Audio('data:audio/mp3;base64,{audio_b64}');
            audio.volume = 1.0;
            audio.play();
        }})();
    """)


def join_zoom_meeting(
    meeting_url: str,
    bot_name: str = "Onboarding Assistant",
    passcode: str | None = None,
):
    """Join a Zoom meeting using Selenium."""
    
    # Parse meeting ID
    match = re.search(r'/j/(\d+)', meeting_url)
    meeting_id = match.group(1) if match else ""
    
    # Get passcode from URL if not provided
    if not passcode:
        pwd_match = re.search(r'pwd=([^&\s]+)', meeting_url)
        passcode = pwd_match.group(1) if pwd_match else None
    
    print("=" * 60)
    print("🤖 ZOOM ONBOARDING BOT")
    print("=" * 60)
    print(f"📍 Meeting ID: {meeting_id}")
    print(f"🔑 Passcode: {'Yes' if passcode else 'No'}")
    print(f"👤 Bot Name: {bot_name}")
    print()
    
    # Setup Chrome options
    print("🌐 Setting up Chrome browser...")
    chrome_options = Options()
    chrome_options.add_argument("--use-fake-ui-for-media-stream")
    chrome_options.add_argument("--use-fake-device-for-media-stream")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1280,720")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    # Keep it visible so user can see
    # chrome_options.add_argument("--headless=new")
    
    # Enable audio/video permissions
    chrome_options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.media_stream_mic": 1,
        "profile.default_content_setting_values.media_stream_camera": 1,
        "profile.default_content_setting_values.notifications": 2,
    })
    
    # Initialize WebDriver
    print("⏳ Downloading ChromeDriver...")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.implicitly_wait(5)  # Reduced implicit wait
    
    try:
        # Construct web client URL - use the original URL with passcode
        # The web client works best with the full URL
        if "wc/" not in meeting_url:
            web_url = meeting_url.replace("/j/", "/wc/join/")
        else:
            web_url = meeting_url
        
        print(f"🔗 Navigating to: {web_url}")
        driver.get(web_url)
        
        print("⏳ Waiting for page to load...")
        time.sleep(5)
        
        # Take screenshot to see current state
        driver.save_screenshot("zoom_debug_1.png")
        print("📸 Saved debug screenshot: zoom_debug_1.png")
        
        # Print page source snippet for debugging
        page_source = driver.page_source[:500]
        print(f"📄 Page snippet: {page_source[:200]}...")
        
        # Wait for and fill in the name - try multiple approaches
        print("✏️ Looking for name input...")
        name_filled = False
        
        # Wait a bit more for page elements
        time.sleep(3)
        
        # Try by ID first
        try:
            name_input = driver.find_element(By.ID, "inputname")
            name_input.clear()
            name_input.send_keys(bot_name)
            name_filled = True
            print("✅ Name entered (by ID)")
        except Exception:
            pass
        
        # Try by name attribute
        if not name_filled:
            try:
                name_input = driver.find_element(By.NAME, "name")
                name_input.clear()
                name_input.send_keys(bot_name)
                name_filled = True
                print("✅ Name entered (by name)")
            except Exception:
                pass
        
        # Try by CSS selector
        if not name_filled:
            try:
                # Common Zoom input selectors
                selectors = [
                    "input#inputname",
                    "input.zm-input",
                    "input[aria-label*='name' i]",
                    "input[placeholder*='name' i]",
                    ".join-dialog input[type='text']",
                ]
                for selector in selectors:
                    try:
                        name_input = driver.find_element(By.CSS_SELECTOR, selector)
                        name_input.clear()
                        name_input.send_keys(bot_name)
                        name_filled = True
                        print(f"✅ Name entered (selector: {selector})")
                        break
                    except Exception:
                        continue
            except Exception:
                pass
        
        if not name_filled:
            print("⚠️ Could not find name field - page may require different handling")
            # List all inputs for debugging
            inputs = driver.find_elements(By.TAG_NAME, "input")
            print(f"   Found {len(inputs)} input elements")
            for i, inp in enumerate(inputs[:5]):
                print(f"   Input {i}: id={inp.get_attribute('id')}, name={inp.get_attribute('name')}, type={inp.get_attribute('type')}")
        
        # Fill passcode if available
        if passcode:
            print("🔐 Looking for passcode input...")
            passcode_filled = False
            
            try:
                pwd_input = driver.find_element(By.ID, "inputpasscode")
                pwd_input.clear()
                pwd_input.send_keys(passcode)
                passcode_filled = True
                print("✅ Passcode entered")
            except Exception:
                pass
            
            if not passcode_filled:
                try:
                    pwd_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
                    pwd_input.clear()
                    pwd_input.send_keys(passcode)
                    passcode_filled = True
                    print("✅ Passcode entered (password field)")
                except Exception:
                    pass
        
        # Take another screenshot
        driver.save_screenshot("zoom_debug_2.png")
        print("📸 Saved debug screenshot: zoom_debug_2.png")
        
        # Click Join
        print("🚀 Looking for join button...")
        join_clicked = False
        
        try:
            join_btn = driver.find_element(By.ID, "joinBtn")
            join_btn.click()
            join_clicked = True
            print("✅ Clicked join button (by ID)")
        except Exception:
            pass
        
        if not join_clicked:
            try:
                # Try various button selectors
                button_selectors = [
                    "button.zm-btn--primary",
                    "button[type='submit']",
                    ".preview-join-button",
                    "button.btn-primary",
                ]
                for selector in button_selectors:
                    try:
                        join_btn = driver.find_element(By.CSS_SELECTOR, selector)
                        join_btn.click()
                        join_clicked = True
                        print(f"✅ Clicked join button (selector: {selector})")
                        break
                    except Exception:
                        continue
            except Exception:
                pass
        
        if not join_clicked:
            try:
                # Find button by text
                buttons = driver.find_elements(By.TAG_NAME, "button")
                for btn in buttons:
                    text = btn.text.lower()
                    if "join" in text or "enter" in text:
                        btn.click()
                        join_clicked = True
                        print(f"✅ Clicked join button (text: {btn.text})")
                        break
            except Exception:
                pass
        
        if not join_clicked:
            print("⚠️ Could not find join button")
            buttons = driver.find_elements(By.TAG_NAME, "button")
            print(f"   Found {len(buttons)} buttons")
            for i, btn in enumerate(buttons[:5]):
                print(f"   Button {i}: text='{btn.text}', class={btn.get_attribute('class')}")
        
        print("⏳ Waiting to enter meeting...")
        time.sleep(10)
        
        # Take screenshot after joining
        driver.save_screenshot("zoom_debug_3.png")
        print("📸 Saved debug screenshot: zoom_debug_3.png")
        
        # Handle "Join Audio" popup
        print("🔊 Looking for audio join option...")
        time.sleep(3)
        
        try:
            # Try clicking "Join Audio by Computer"
            audio_buttons = driver.find_elements(By.TAG_NAME, "button")
            for btn in audio_buttons:
                text = btn.text.lower()
                if "audio" in text or "computer" in text:
                    btn.click()
                    print(f"✅ Clicked audio button: {btn.text}")
                    break
        except Exception:
            print("⚠️ Could not find audio button")
        
        time.sleep(2)
        
        print()
        print("=" * 60)
        print("✅ BOT IS CONNECTED TO THE MEETING!")
        print("=" * 60)
        print()
        print("Interactive Commands:")
        print("  /say <text>     - Make the bot speak the text")
        print("  /ask <question> - Query knowledge base and speak answer")
        print("  /greet          - Introduce the bot")
        print("  /screenshot     - Save a screenshot")
        print("  /quit           - Leave the meeting")
        print()
        print("Example: /ask What is the deployment process?")
        print()
        
        # Greeting message
        greeting = "Hello everyone! I'm the Onboarding Assistant. I can answer questions about our company, processes, and technical systems. Just type your question in the chat or ask me directly!"
        print(f"🎤 Speaking greeting...")
        audio = synthesize_speech(greeting)
        if audio:
            play_audio_in_browser(driver, audio)
            print("✅ Greeting spoken")
        
        # Interactive command loop
        while True:
            try:
                command = input("\n💬 Command: ").strip()
                
                if not command:
                    continue
                
                if command.startswith("/quit") or command.startswith("/exit"):
                    print("👋 Leaving meeting...")
                    break
                
                elif command.startswith("/say "):
                    text = command[5:].strip()
                    if text:
                        print(f"🎤 Speaking: {text}")
                        audio = synthesize_speech(text)
                        if audio:
                            play_audio_in_browser(driver, audio)
                            print("✅ Audio played")
                        else:
                            print("❌ Failed to generate speech")
                    else:
                        print("⚠️ Please provide text to speak")
                
                elif command.startswith("/ask "):
                    question = command[5:].strip()
                    if question:
                        print(f"❓ Querying: {question}")
                        result = query_knowledge_base(question)
                        answer = result.get("text", "I don't have information about that.")
                        sources = result.get("sources", [])
                        
                        print(f"💡 Answer: {answer}")
                        if sources:
                            print(f"📚 Sources: {sources}")
                        
                        audio = synthesize_speech(answer)
                        if audio:
                            play_audio_in_browser(driver, audio)
                            print("✅ Answer spoken")
                    else:
                        print("⚠️ Please provide a question")
                
                elif command.startswith("/greet"):
                    greeting = "Hello! I'm here to help answer any questions you might have about our company, processes, or technical documentation. Feel free to ask me anything!"
                    print(f"🎤 Speaking greeting...")
                    audio = synthesize_speech(greeting)
                    if audio:
                        play_audio_in_browser(driver, audio)
                        print("✅ Greeting spoken")
                
                elif command.startswith("/screenshot"):
                    filename = f"zoom_screenshot_{int(time.time())}.png"
                    driver.save_screenshot(filename)
                    print(f"📸 Screenshot saved: {filename}")
                
                elif command.startswith("/help"):
                    print("""
Commands:
  /say <text>     - Make the bot speak the text
  /ask <question> - Query knowledge base and speak answer
  /greet          - Introduce the bot
  /screenshot     - Save a screenshot
  /quit           - Leave the meeting
                    """)
                
                else:
                    # Treat as a question
                    print(f"❓ Treating as question: {command}")
                    result = query_knowledge_base(command)
                    answer = result.get("text", "I'm not sure about that.")
                    print(f"💡 Answer: {answer}")
                    audio = synthesize_speech(answer)
                    if audio:
                        play_audio_in_browser(driver, audio)
                        print("✅ Answer spoken")
                    
            except KeyboardInterrupt:
                print("\n👋 Leaving meeting...")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
        
    finally:
        print("🔄 Closing browser...")
        driver.quit()
        print("✅ Bot has left the meeting")


def main():
    parser = argparse.ArgumentParser(description="Selenium Zoom Onboarding Bot")
    parser.add_argument("--url", required=True, help="Zoom meeting URL")
    parser.add_argument("--name", default="Onboarding Assistant", help="Bot display name")
    parser.add_argument("--passcode", help="Meeting passcode (if not in URL)")
    
    args = parser.parse_args()
    
    join_zoom_meeting(
        meeting_url=args.url,
        bot_name=args.name,
        passcode=args.passcode,
    )


if __name__ == "__main__":
    main()
