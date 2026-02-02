export interface SlackMessage {
  user?: string;
  text?: string;
}

export interface GeminiContent {
  role: "user" | "model";
  parts: { text: string }[];
}
