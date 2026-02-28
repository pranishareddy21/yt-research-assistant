YT Research Assistant

Telegram YouTube Summarizer & Q&A Bot

Project Overview

YT Research Assistant is a Telegram bot that helps users quickly understand and interact with long YouTube videos.

The system allows users to:

Submit a YouTube link

Receive a structured summary

Ask contextual follow-up questions

Extract actionable insights

Request responses in multiple Indian languages

Core Features
Structured Summary

When a YouTube link is submitted, the bot returns:

Video Title

5 Key Points

Important Timestamps

Core Takeaway

Contextual Q&A

After processing a video, users can ask follow-up questions.

The bot:

Retrieves relevant transcript sections

Generates answers grounded strictly in the transcript

Returns:
"This topic is not covered in the video."
if information is missing

Action Points

Users can request:

action points

The bot extracts practical insights from the video.

Multi-language Support

Supported languages:

English (default)

Hindi

Telugu

Tamil

Kannada

Marathi

Architecture

Flow:

Telegram
→ Transcript Retrieval
→ Text Chunking
→ Context Ranking
→ LLM Processing
→ Structured Output

Setup

Clone repository:

git clone https://github.com/pranishareddy21/yt-research-assistant.git
cd yt-research-assistant

Install dependencies:

pip install -r requirements.txt

Create .env file:

BOT_TOKEN=your_telegram_bot_token
GROQ_API_KEY=your_groq_api_key

Run:

python bot.py
Edge Cases Handled

Invalid YouTube URL

Missing transcript

Long videos

Multi-user sessions

Follow-up without prior video

Future Improvements

Embedding-based semantic search

Persistent session storage

Transcript caching

Cloud deployment
