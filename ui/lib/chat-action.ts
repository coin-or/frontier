"use client";

import { createContext, useContext } from "react";

export type ChatAction = {
  /** Send a message to the agent as if the user typed it. */
  sendMessage: (text: string) => void;
  /** True while the agent is streaming (sends are no-ops then). */
  streaming: boolean;
};

export const ChatActionContext = createContext<ChatAction | null>(null);

export function useChatAction(): ChatAction | null {
  return useContext(ChatActionContext);
}
