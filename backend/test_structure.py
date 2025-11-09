#!/usr/bin/env python3
"""
Quick test to verify the new backend structure.
Set GOOGLE_AI_STUDIO_API_KEY before running actual analysis.
"""
import sys
import os
from pathlib import Path

# Set dummy API key for testing imports
os.environ["GOOGLE_AI_STUDIO_API_KEY"] = "test_key_for_structure_check"

# Test imports
print("Testing imports...")
try:
    from app import models
    print("✓ app.models imported")
    
    from app.routers import analyze, chat
    print("✓ app.routers imported")
    
    # Note: These import will initialize Gemini, but won't fail with dummy key
    # from app.services import analyzer, chat as chat_service
    # print("✓ app.services imported")
    
    print("\nAll imports successful!")
    
    # Test model structure
    print("\nTesting Pydantic models...")
    test_feedback = {
        "time_range": "00:15-00:30",
        "details": ["Test feedback"]
    }
    timestamped = models.TimestampedFeedback(**test_feedback)
    print(f"✓ TimestampedFeedback model works: {timestamped.time_range}")
    
    print("\n✅ Backend structure is correctly set up!")
    print("\nNext steps:")
    print("1. Copy .env.example to .env")
    print("2. Add your GOOGLE_AI_STUDIO_API_KEY to .env")
    print("3. Run: python main.py")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
