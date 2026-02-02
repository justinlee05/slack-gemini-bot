import { GoogleGenAI } from "@google/genai";
import { GEMINI_API_KEY, SLACK_BOT_USER_ID } from "./constants";
import { GeminiContent, SlackMessage } from "./types";

// Init Gemini client
const genai = new GoogleGenAI({ apiKey: GEMINI_API_KEY! });

export async function callGemini(
  modelName: string,
  contents: GeminiContent[],
  systemInstruction: string,
  useGoogleSearch: boolean = false
): Promise<string> {
  const tools = useGoogleSearch ? [{ googleSearch: {} }] : undefined;

  const response = await genai.models.generateContent({
    model: modelName,
    contents,
    config: {
      systemInstruction,
      tools,
      thinkingConfig: {
        thinkingBudget: 1024, // 0~24576 범위, 낮을수록 추론 적음
      },
    },
  });

  return (response.text || "").trim();
}

export function buildGeminiContentsFromThread(
  historyMessages: SlackMessage[]
): GeminiContent[] {
  const contents: GeminiContent[] = [];

  for (const msg of historyMessages) {
    const text = msg.text || "";
    const isBot = msg.user === SLACK_BOT_USER_ID;
    const role: "user" | "model" = isBot ? "model" : "user";

    contents.push({
      role,
      parts: [{ text }],
    });
  }

  return contents;
}
