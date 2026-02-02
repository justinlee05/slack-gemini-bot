import * as dotenv from "dotenv";

dotenv.config();

const env = process.env;

// Env vars (Slack)
export const SLACK_BOT_TOKEN = env.SLACK_BOT_TOKEN ?? "";
export const SLACK_APP_TOKEN = env.SLACK_APP_TOKEN ?? "";
export const SLACK_BOT_USER_ID = env.SLACK_BOT_USER_ID ?? "";

// Env vars (Gemini)
export const GEMINI_API_KEY = env.GEMINI_API_KEY ?? "";

// Build system instructions with bot identity info (from env or default)
const _baseInstructions = env.SLACK_CUSTOM_INSTRUCTIONS ?? "";
const _botIdentity = env.SLACK_BOT_IDENTITY_INSTRUCTION ?? "";

export const SLACK_CUSTOM_INSTRUCTIONS = `${_baseInstructions}\n${_botIdentity}`;

export const GEMINI_MODEL = env.GEMINI_MODEL ?? "";
export const GEMINI_SEARCH_MODEL = env.GEMINI_SEARCH_MODEL ?? "";
export const GEMINI_CONTEXT_WINDOW = parseInt(
  env.GEMINI_CONTEXT_WINDOW ?? "10",
  10
);
export const GEMINI_SEARCH_REQUIRED_IDENTIFIER =
  env.GEMINI_SEARCH_REQUIRED_IDENTIFIER ?? "";
