import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    filters,
    ContextTypes,
)
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
from groq import Groq

# ==============================
# Load Environment Variables
# ==============================
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not TOKEN:
    raise ValueError("BOT_TOKEN not found in .env file")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in .env file")

client = Groq(api_key=GROQ_API_KEY)

print("Bot starting...")

# ==============================
# In-memory session storage
# ==============================
user_data_store = {}

SUPPORTED_LANGUAGES = {
    "hindi": "Hindi",
    "telugu": "Telugu",
    "tamil": "Tamil",
    "kannada": "Kannada",
    "marathi": "Marathi",
}

# ==============================
# Helper Functions
# ==============================

def extract_video_id(url):
    try:
        if "youtu.be" in url:
            return url.split("/")[-1]
        elif "youtube.com" in url:
            parsed_url = urlparse(url)
            return parse_qs(parsed_url.query).get("v", [None])[0]
        return None
    except:
        return None


from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

def get_transcript(video_id):
    try:
        transcript_list = YouTubeTranscriptApi().list(video_id)

        # Try English first
        try:
            transcript = transcript_list.find_transcript(['en'])
        except:
            # Fallback to first available transcript
            transcript = transcript_list.find_transcript(
                [t.language_code for t in transcript_list]
            )

        fetched = transcript.fetch()

        transcript_text = ""
        timestamped_text = ""

        for entry in fetched:
            minutes = int(entry.start // 60)
            seconds = int(entry.start % 60)
            time_str = f"{minutes:02d}:{seconds:02d}"

            transcript_text += entry.text + " "
            timestamped_text += f"[{time_str}] {entry.text}\n"

        words = transcript_text.split()
        transcript_text = " ".join(words[:3000])

        return transcript_text, timestamped_text

    except (TranscriptsDisabled, NoTranscriptFound):
        raise Exception("Transcript not available")
    except Exception:
        raise Exception("Transcript retrieval failed")

def chunk_text(text, chunk_size=250):
    words = text.split()
    return [
        " ".join(words[i:i + chunk_size])
        for i in range(0, len(words), chunk_size)
    ]


def simple_similarity(question, chunk):
    q_words = set(question.lower().split())
    c_words = set(chunk.lower().split())
    return len(q_words.intersection(c_words)) / (len(q_words) + 1)


def detect_language(text):
    for key, value in SUPPORTED_LANGUAGES.items():
        if key in text.lower():
            return value
    return "English"


def generate_summary(timestamped_text, language="English"):
    prompt = f"""
Summarize this YouTube transcript in under 150 words.

Respond strictly in {language}.

Format:

🎥 Video Title:
📌 5 Key Points:
⏱ Important Timestamps (3–5 major moments):
🧠 Core Takeaway:

Transcript with timestamps:
{timestamped_text[:3000]}
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )

    return response.choices[0].message.content


def generate_answer(question, context, language="English"):
    prompt = f"""
Answer strictly using the context below.
Respond in {language}.
If answer is not present, say:
"This topic is not covered in the video."

Context:
{context}

Question:
{question}
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    return response.choices[0].message.content


def generate_action_points(context, language="English"):
    prompt = f"""
Extract actionable insights from the video context below.

Respond in {language}.

Format:
📌 Actionable Insights:
- ...
- ...
- ...

Context:
{context}
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )

    return response.choices[0].message.content


# ==============================
# Telegram Handlers
# ==============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to YT Research Assistant!\n\n"
        "Send a YouTube link to generate a summary.\n"
        "Ask follow-up questions.\n"
        "Type 'action points' for key insights.\n"
        "You can request Hindi, Telugu, Tamil, Kannada, Marathi."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    language = detect_language(text)

    # ==========================
    # YouTube Link
    # ==========================
    if "youtube.com" in text or "youtu.be" in text:
        await update.message.reply_text("🎥 Fetching transcript...")

        video_id = extract_video_id(text)

        if not video_id:
            await update.message.reply_text("❌ Invalid YouTube link.")
            return

        try:
            transcript, timestamped_text = get_transcript(video_id)
        except:
            await update.message.reply_text(
                "❌ Could not retrieve transcript for this video."
            )
            return

        chunks = chunk_text(transcript)

        user_data_store[user_id] = {
            "chunks": chunks,
            "language": language,
        }

        await update.message.reply_text(
            "🧠 Analyzing video and generating structured insights..."
        )

        summary = generate_summary(timestamped_text, language)

        await update.message.reply_text(summary)

    # ==========================
    # Action Points
    # ==========================
    elif "action points" in text.lower() and user_id in user_data_store:
        await update.message.reply_text("📌 Extracting actionable insights...")

        chunks = user_data_store[user_id]["chunks"]
        language = user_data_store[user_id]["language"]

        context_text = "\n\n".join(chunks[:3])

        action_points = generate_action_points(context_text, language)

        await update.message.reply_text(action_points)

    # ==========================
    # Follow-up Q&A
    # ==========================
    elif user_id in user_data_store:
        await update.message.reply_text("🔎 Retrieving relevant context...")

        chunks = user_data_store[user_id]["chunks"]
        language = user_data_store[user_id]["language"]

        scored_chunks = sorted(
            chunks,
            key=lambda c: simple_similarity(text, c),
            reverse=True,
        )

        context_text = "\n\n".join(scored_chunks[:2])

        answer = generate_answer(text, context_text, language)

        await update.message.reply_text(answer)

    # ==========================
    # Default
    # ==========================
    else:
        await update.message.reply_text(
            "Send a YouTube link first to begin 🚀"
        )


# ==============================
# Start Bot
# ==============================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT, handle_message))

print("Bot started...")
app.run_polling()