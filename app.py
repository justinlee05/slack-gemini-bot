import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient

# Google Gen AI SDK (Gemini Developer API / Vertex AI 통합 SDK)
from google import genai
from google.genai import types

# Load environment variables
load_dotenv()

# Defaults (keep behavior close to the original bot)
DEFAULT_SYSTEM_INSTRUCTIONS = "You are a helpful assistant inside Slack. Keep responses helpful but concise."
DEFAULT_GEMINI_MODEL = "gemini-3-flash-preview"
DEFAULT_GEMINI_SEARCH_MODEL = "gemini-3-flash-preview"  # you may keep same model; search is enabled via tool config
DEFAULT_CONTEXT_WINDOW = 10
DEFAULT_GEMINI_SEARCH_REQUIRED_IDENTIFIER = "SLACK_BOT_WEB_SEARCH_REQUIRED"

# Env vars (Slack)
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
SLACK_BOT_USER_ID = os.getenv("SLACK_BOT_USER_ID")

# Env vars (Gemini)
# The Client can automatically pick up GEMINI_API_KEY from environment variables.
# Still, you can pass it explicitly if you want.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

SLACK_CUSTOM_INSTRUCTIONS = os.getenv("SLACK_CUSTOM_INSTRUCTIONS", DEFAULT_SYSTEM_INSTRUCTIONS)
GEMINI_MODEL = os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
GEMINI_SEARCH_MODEL = os.getenv("GEMINI_SEARCH_MODEL", DEFAULT_GEMINI_SEARCH_MODEL)
GEMINI_CONTEXT_WINDOW = int(os.getenv("GEMINI_CONTEXT_WINDOW", DEFAULT_CONTEXT_WINDOW))
GEMINI_SEARCH_REQUIRED_IDENTIFIER = os.getenv(
    "GEMINI_SEARCH_REQUIRED_IDENTIFIER",
    DEFAULT_GEMINI_SEARCH_REQUIRED_IDENTIFIER,
)

# Basic validation (fail fast)
missing = []
if not SLACK_BOT_TOKEN:
    missing.append("SLACK_BOT_TOKEN")
if not SLACK_APP_TOKEN:
    missing.append("SLACK_APP_TOKEN")
if not SLACK_BOT_USER_ID:
    missing.append("SLACK_BOT_USER_ID")
if not GEMINI_API_KEY:
    missing.append("GEMINI_API_KEY (or GOOGLE_API_KEY)")

if missing:
    raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")

# Init Slack clients
app = App(token=SLACK_BOT_TOKEN)
slack_client = WebClient(token=SLACK_BOT_TOKEN)

# Init Gemini client
# According to the SDK docs, if GEMINI_API_KEY is set, Client() picks it up automatically.
# Passing it explicitly is fine too.
gemini_client = genai.Client(api_key=GEMINI_API_KEY)


def build_gemini_contents_from_thread(history_messages):
    """
    Convert Slack thread messages into Gemini contents.
    Gemini roles: 'user' and 'model'
    """
    contents = []
    for msg in history_messages:
        text = msg.get("text", "")
        is_bot = (msg.get("user") == SLACK_BOT_USER_ID)
        role = "model" if is_bot else "user"

        # Use typed Content + Part to avoid SDK conversion edge cases
        contents.append(
            types.Content(
                role=role,
                parts=[types.Part(text=text)],
            )
        )
    return contents


def call_gemini(model_name, contents, system_instruction, use_google_search=False):
    """
    Make a Gemini generate_content call.
    - system_instruction: passed via GenerateContentConfig
    - use_google_search: enable google_search tool grounding (server-side search)
    """
    tools = None
    if use_google_search:
        grounding_tool = types.Tool(google_search=types.GoogleSearch())
        tools = [grounding_tool]

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=tools,
    )

    response = gemini_client.models.generate_content(
        model=model_name,
        contents=contents,
        config=config,
    )

    # The SDK exposes response.text for the primary text
    return (response.text or "").strip()


@app.event("app_mention")
def handle_mentions(body, say):
    event = body["event"]
    channel = event["channel"]
    thread_ts = event.get("thread_ts", event["ts"])

    try:
        # Get last N messages from the thread (same behavior)
        history = slack_client.conversations_replies(channel=channel, ts=thread_ts).get("messages", [])
        history = history[-GEMINI_CONTEXT_WINDOW:]

        # Build Gemini contents from thread history
        contents = build_gemini_contents_from_thread(history)

        # 1st pass (no search tool)
        text = call_gemini(
            model_name=GEMINI_MODEL,
            contents=contents,
            system_instruction=SLACK_CUSTOM_INSTRUCTIONS,
            use_google_search=False,
        )

        # If search is required, do a 2nd pass with google_search tool enabled
        if GEMINI_SEARCH_REQUIRED_IDENTIFIER in text:
            text = call_gemini(
                model_name=GEMINI_SEARCH_MODEL,
                contents=contents,
                system_instruction=SLACK_CUSTOM_INSTRUCTIONS,
                use_google_search=True,
            )
            text = (text + "\n\n🌐 (Used web search)").strip()

        say(text=text, thread_ts=thread_ts)

    except Exception as e:
        # Keep same style as original bot
        say(text=f"⚠️ Error: {str(e)}", thread_ts=thread_ts)


if __name__ == "__main__":
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()
