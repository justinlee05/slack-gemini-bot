import { App } from "@slack/bolt";
import {
  GEMINI_API_KEY,
  GEMINI_CONTEXT_WINDOW,
  GEMINI_MODEL,
  GEMINI_SEARCH_MODEL,
  GEMINI_SEARCH_REQUIRED_IDENTIFIER,
  SLACK_APP_TOKEN,
  SLACK_BOT_TOKEN,
  SLACK_BOT_USER_ID,
  SLACK_CUSTOM_INSTRUCTIONS,
} from "./constants";
import { SlackMessage } from "./types";
import { buildGeminiContentsFromThread, callGemini } from "./genAI";

// Basic validation (fail fast)
const missing: string[] = [];
if (!SLACK_BOT_TOKEN) missing.push("SLACK_BOT_TOKEN");
if (!SLACK_APP_TOKEN) missing.push("SLACK_APP_TOKEN");
if (!SLACK_BOT_USER_ID) missing.push("SLACK_BOT_USER_ID");
if (!GEMINI_API_KEY) missing.push("GEMINI_API_KEY (or GOOGLE_API_KEY)");

if (missing.length > 0) {
  throw new Error(`Missing required env vars: ${missing.join(", ")}`);
}

// Init Slack app (Socket Mode)
const app = new App({
  token: SLACK_BOT_TOKEN,
  appToken: SLACK_APP_TOKEN,
  socketMode: true,
});

// Handle app mentions
app.event("app_mention", async ({ event, say }) => {
  // Prevent infinite loops by checking if the event is from a bot
  if (event.bot_id || event.bot_profile) {
    console.log("The bot is mentioned by another bot. Skipping...");
    return;
  }
  const channel = event.channel;
  const threadTs = event.thread_ts || event.ts;

  try {
    // Get last N messages from the thread
    const result = await app.client.conversations.replies({
      token: SLACK_BOT_TOKEN,
      channel,
      ts: threadTs,
    });

    const history = (result.messages || []).slice(-GEMINI_CONTEXT_WINDOW);

    // Build Gemini contents from thread history
    const contents = buildGeminiContentsFromThread(history as SlackMessage[]);

    // 1st pass (no search tool)
    let text = await callGemini(
      GEMINI_MODEL,
      contents,
      SLACK_CUSTOM_INSTRUCTIONS,
      false
    );

    // If search is required, do a 2nd pass with google_search tool enabled
    if (text.includes(GEMINI_SEARCH_REQUIRED_IDENTIFIER)) {
      text = await callGemini(
        GEMINI_SEARCH_MODEL,
        contents,
        SLACK_CUSTOM_INSTRUCTIONS,
        true
      );
      text = `${text}\n\n🌐 (Used web search)`.trim();
    }

    await say({ text, thread_ts: threadTs });
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    await say({ text: `⚠️ Error: ${errorMessage}`, thread_ts: threadTs });
  }
});

// Start the app
(async () => {
  await app.start();
  console.log("⚡️ Slack Gemini Bot is running!");
})();
