#!/usr/bin/env python3
"""
CLI test script for the new OpenAI structured output functionality with Pydantic models.
"""

import os
import sys
from typing import List, Optional

from dotenv import load_dotenv
from openai_client import OpenAIClient
from pydantic import BaseModel, Field

load_dotenv()


# Example Pydantic models for testing
class CalendarEvent(BaseModel):
    """Model for calendar event information"""

    name: str = Field(description="The name or title of the event")
    date: str = Field(description="The date of the event")
    participants: List[str] = Field(
        description="List of people participating in the event"
    )
    location: Optional[str] = Field(default=None, description="Location of the event")
    description: Optional[str] = Field(
        default=None, description="Description of the event"
    )


class RoomAnalysis(BaseModel):
    """Model for room analysis results"""

    room_type: str = Field(
        description="Type of room (bedroom, living room, kitchen, etc.)"
    )
    dimensions: Optional[str] = Field(
        default=None, description="Room dimensions if mentioned"
    )
    current_furniture: List[str] = Field(description="List of current furniture items")
    style_preferences: List[str] = Field(description="Style preferences mentioned")
    improvement_suggestions: List[str] = Field(description="Suggested improvements")
    color_scheme: Optional[str] = Field(
        default=None, description="Recommended color scheme"
    )


class ContactInfo(BaseModel):
    """Model for contact information extraction"""

    name: str = Field(description="Full name of the person")
    email: Optional[str] = Field(default=None, description="Email address")
    phone: Optional[str] = Field(default=None, description="Phone number")
    company: Optional[str] = Field(default=None, description="Company or organization")
    title: Optional[str] = Field(default=None, description="Job title or role")


def test_calendar_event_extraction():
    """Test calendar event extraction using the exact approach from the example"""
    print("🔍 Testing Calendar Event Extraction...")

    client = OpenAIClient()

    try:
        event = client.get_structured_completion(
            prompt="Alice and Bob are going to a science fair on Friday.",
            pydantic_model=CalendarEvent,
            system_message="Extract the event information.",
        )

        print("✅ Successfully extracted event:")
        print(f"   Name: {event.name}")
        print(f"   Date: {event.date}")
        print(f"   Participants: {', '.join(event.participants)}")
        print(f"   Location: {event.location}")
        print(f"   Description: {event.description}")

    except Exception as e:
        print(f"❌ Error: {e}")


def test_room_analysis():
    """Test room analysis"""
    print("\n🏠 Testing Room Analysis...")

    client = OpenAIClient()

    prompt = """
    I have a small bedroom that's about 12x10 feet. Currently it has a queen bed, 
    a small desk, and a bookshelf. I love Scandinavian design and want a minimalist 
    look with lots of natural light. I prefer neutral colors like whites, grays, and 
    light wood tones.
    """

    try:
        analysis = client.get_structured_completion(
            prompt=prompt,
            pydantic_model=RoomAnalysis,
            system_message="Analyze the room description and provide detailed recommendations for interior design improvements.",
        )

        print("✅ Successfully analyzed room:")
        print(f"   Room Type: {analysis.room_type}")
        print(f"   Dimensions: {analysis.dimensions}")
        print(f"   Current Furniture: {', '.join(analysis.current_furniture)}")
        print(f"   Style Preferences: {', '.join(analysis.style_preferences)}")
        print(
            f"   Improvement Suggestions: {', '.join(analysis.improvement_suggestions)}"
        )
        print(f"   Color Scheme: {analysis.color_scheme}")

    except Exception as e:
        print(f"❌ Error: {e}")


def test_contact_info_extraction():
    """Test contact information extraction"""
    print("\n📞 Testing Contact Information Extraction...")

    client = OpenAIClient()

    prompt = "John Smith is a Senior Software Engineer at TechCorp. You can reach him at john.smith@techcorp.com or call him at (555) 123-4567."

    try:
        contact = client.get_structured_completion(
            prompt=prompt,
            pydantic_model=ContactInfo,
            system_message="Extract contact information from the given text. Only include information that is explicitly provided.",
        )

        print("✅ Successfully extracted contact info:")
        print(f"   Name: {contact.name}")
        print(f"   Email: {contact.email}")
        print(f"   Phone: {contact.phone}")
        print(f"   Company: {contact.company}")
        print(f"   Title: {contact.title}")

    except Exception as e:
        print(f"❌ Error: {e}")


def test_direct_example():
    """Test the exact example from the user"""
    print("\n🎯 Testing Direct Example...")

    client = OpenAIClient()

    try:
        event = client.get_structured_completion(
            prompt="Alice and Bob are going to a science fair on Friday.",
            pydantic_model=CalendarEvent,
            system_message="Extract the event information.",
        )

        print("✅ Direct example result:")
        print(f"   Event: {event}")

    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    """Main CLI function"""
    print("🚀 OpenAI Structured Output CLI Test")
    print("=" * 50)

    # Check if API key is set
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY environment variable is not set")
        print("Please set your OpenAI API key:")
        print("export OPENAI_API_KEY='your-api-key-here'")
        sys.exit(1)

    # Run tests
    test_direct_example()
    test_calendar_event_extraction()
    test_room_analysis()
    test_contact_info_extraction()

    print("\n🎉 All tests completed!")


if __name__ == "__main__":
    main()
