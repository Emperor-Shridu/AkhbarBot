import asyncio
import sys
import os

# Add parent directory to system path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_components():
    print("1. Testing configuration validation...")
    try:
        from config import Config
        channel = "WhatsApp" if Config.WHATSAPP_ACCESS_TOKEN else "Telegram"
        print(f"   Config loaded. Active channel available: {channel}")
    except Exception as e:
        print(f"   [ERROR] Config loading failed: {e}")
        return False

    print("2. Testing module imports...")
    try:
        from database import get_db
        from utils.ogg_splitter import split_ogg
        from utils.telegram import send_message
        from utils.whatsapp import send_text
        from agents.audio import AudioChunkAgent
        from agents.ocr import OCRAgent
        from agents.trend import TrendAgent
        from agents.editor import EditorAgent
        from agents.supervisor import SupervisorAgent
        print("   [OK] All modules imported successfully!")
    except Exception as e:
        print(f"   [ERROR] Import failed: {e}")
        return False

    print("3. Testing agent initialization...")
    try:
        supervisor = SupervisorAgent()
        print("   [OK] SupervisorAgent initialized successfully!")
    except Exception as e:
        print(f"   [ERROR] Agent initialization failed: {e}")
        return False

    print("4. Testing pure-python Ogg page segmenter...")
    try:
        # Create a mock Ogg header stream
        mock_ogg_data = (
            b"OggS" + b"\x00" * 22 + b"\x01" + b"\x00" + # Page 1 (BOF header, 28 bytes)
            b"OggS" + b"\x00" * 22 + b"\x01" + b"\x00" + # Page 2 (Tags header, 28 bytes)
            b"OggS" + b"\x00" * 2 + b"\x40\x1f\x00\x00\x00\x00\x00\x00" + b"\x00" * 8 + b"\x00" * 4 + b"\x01" + b"\x00" # Page 3 (Audio page, 28 bytes)
        )
        chunks = split_ogg(mock_ogg_data)

        print(f"   [OK] Splitter processed data. Generated {len(chunks)} chunks.")
    except Exception as e:
        print(f"   [ERROR] Splitter test failed: {e}")
        return False

    print("\nALL STATIC COMPONENT TESTS PASSED SUCCESSFULLY!")
    return True


if __name__ == "__main__":
    success = asyncio.run(test_components())
    if not success:
        sys.exit(1)
