import { ChatView } from "@/components/chat/chat-view";

/** A stored conversation; ChatView reads the id from the URL (it also moves here from "/"). */
export default function ConversationPage() {
  return <ChatView />;
}
