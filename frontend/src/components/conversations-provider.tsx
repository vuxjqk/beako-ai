"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { errorMessage } from "@/lib/errors";
import { qaApi, type ConversationSummary } from "@/lib/qa";

type ConversationsState = {
  items: ConversationSummary[];
  /** false until the first page has loaded */
  loaded: boolean;
  error: string | null;
  hasMore: boolean;
  loadingMore: boolean;
  loadMore: () => void;
  /** Add a conversation or move it to the top (it was just asked in) */
  touch: (conversation: Pick<ConversationSummary, "id" | "title">) => void;
  rename: (id: string, title: string) => Promise<void>;
  remove: (id: string) => Promise<void>;
};

const ConversationsContext = createContext<ConversationsState | null>(null);

/** The signed-in user's conversation list, shared by the sidebar history and the chat. */
export function ConversationsProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<ConversationSummary[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);

  useEffect(() => {
    let cancelled = false;
    qaApi
      .conversations()
      .then((page) => {
        if (cancelled) return;
        // Keep anything touched while the first page was loading
        setItems((current) => [...current, ...page.items.filter((c) => !current.some((x) => x.id === c.id))]);
        setCursor(page.nextCursor);
      })
      .catch((e) => !cancelled && setError(errorMessage(e)))
      .finally(() => !cancelled && setLoaded(true));
    return () => {
      cancelled = true;
    };
  }, []);

  const loadMore = useCallback(() => {
    if (!cursor || loadingMore) return;
    setLoadingMore(true);
    qaApi
      .conversations(cursor)
      .then((page) => {
        setItems((current) => [...current, ...page.items.filter((c) => !current.some((x) => x.id === c.id))]);
        setCursor(page.nextCursor);
      })
      .catch((e) => setError(errorMessage(e)))
      .finally(() => setLoadingMore(false));
  }, [cursor, loadingMore]);

  const touch = useCallback((conversation: Pick<ConversationSummary, "id" | "title">) => {
    setItems((current) => {
      const existing = current.find((c) => c.id === conversation.id);
      const now = new Date().toISOString();
      const entry = existing
        ? { ...existing, updatedAt: now }
        : { ...conversation, createdAt: now, updatedAt: now };
      return [entry, ...current.filter((c) => c.id !== conversation.id)];
    });
  }, []);

  const rename = useCallback(async (id: string, title: string) => {
    const updated = await qaApi.rename(id, title);
    setItems((current) => current.map((c) => (c.id === id ? { ...c, title: updated.title } : c)));
  }, []);

  const remove = useCallback(async (id: string) => {
    await qaApi.remove(id);
    setItems((current) => current.filter((c) => c.id !== id));
  }, []);

  const value = useMemo(
    () => ({ items, loaded, error, hasMore: !!cursor, loadingMore, loadMore, touch, rename, remove }),
    [items, loaded, error, cursor, loadingMore, loadMore, touch, rename, remove],
  );
  return <ConversationsContext.Provider value={value}>{children}</ConversationsContext.Provider>;
}

export function useConversations(): ConversationsState {
  const value = useContext(ConversationsContext);
  if (!value) throw new Error("useConversations must be used inside ConversationsProvider");
  return value;
}

/** "/c/<id>" -> id; anything else -> null. */
export function conversationIdFromPath(pathname: string): string | null {
  const m = /^\/c\/([0-9a-f-]{36})\/?$/i.exec(pathname);
  return m ? m[1] : null;
}
