import { useState, useRef, useEffect, useCallback } from "react"
import { cn } from "@/lib/utils"
import type { ChatMessage, CitationType } from "@/lib/types"
import { sendChatMessage } from "@/lib/api"
import { Button } from "./ui/button"
import { ScrollArea } from "./ui/scroll-area"
import { Send, MessageSquare, Sparkles } from "lucide-react"

const DEFAULT_SUGGESTIONS = [
  "What document types were detected?",
  "Show me all contradictions",
  "Summarize the taxonomy",
  "Which entities need review?",
]

interface ChatPanelProps {
  hasTaxonomy: boolean
}

export function ChatPanel({ hasTaxonomy }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState("")
  const [isTyping, setIsTyping] = useState(false)
  const [suggestions, setSuggestions] = useState<string[]>(DEFAULT_SUGGESTIONS)
  const [sessionId] = useState(() => crypto.randomUUID())
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, isTyping, scrollToBottom])

  const handleSend = async (text?: string) => {
    const message = text ?? input.trim()
    if (!message) return

    const userMessage: ChatMessage = { role: "user", content: message }
    setMessages((prev) => [...prev, userMessage])
    setInput("")
    setIsTyping(true)

    try {
      const response = await sendChatMessage(message, sessionId)
      const assistantMessage: ChatMessage = {
        role: "assistant",
        content: response.response,
        citations: response.citations,
        suggested_queries: response.suggested_queries,
      }
      setMessages((prev) => [...prev, assistantMessage])
      if (response.suggested_queries.length > 0) {
        setSuggestions(response.suggested_queries)
      }
    } catch (err) {
      const errorMessage: ChatMessage = {
        role: "assistant",
        content:
          "Sorry, I encountered an error processing your request. Please try again.",
      }
      setMessages((prev) => [...prev, errorMessage])
      console.error("Chat error:", err)
    } finally {
      setIsTyping(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const renderCitation = (citation: CitationType, index: number) => {
    const colorMap = {
      taxonomy: "bg-indigo-500/20 text-indigo-300 border-indigo-500/30",
      document: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
    }
    return (
      <button
        key={index}
        className={cn(
          "inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-[10px] font-medium transition-colors hover:opacity-80",
          colorMap[citation.type]
        )}
        title={citation.detail}
      >
        {citation.source}
        {citation.page !== null && <span>p.{citation.page}</span>}
      </button>
    )
  }

  const renderMessage = (msg: ChatMessage, index: number) => {
    const isUser = msg.role === "user"
    return (
      <div
        key={index}
        className={cn(
          "flex animate-slide-in",
          isUser ? "justify-end" : "justify-start"
        )}
        style={{ animationDelay: "0ms" }}
      >
        <div
          className={cn(
            "max-w-[85%] rounded-lg px-3 py-2 text-sm",
            isUser
              ? "bg-indigo-600 text-white"
              : "bg-zinc-800 text-zinc-200"
          )}
        >
          <div className="whitespace-pre-wrap">{msg.content}</div>
          {msg.citations && msg.citations.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {msg.citations.map((c, i) => renderCitation(c, i))}
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-full w-80 flex-col border-l border-zinc-800 bg-zinc-900/30">
      {/* Header */}
      <div className="border-b border-zinc-800 p-4">
        <div className="flex items-center gap-2">
          <MessageSquare className="h-4 w-4 text-indigo-400" />
          <h2 className="text-sm font-semibold text-zinc-200">Chat</h2>
        </div>
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1 p-4">
        <div className="space-y-3">
          {messages.length === 0 && (
            <div className="flex flex-col items-center py-8 text-center">
              <div className="rounded-full bg-zinc-800/50 p-3 mb-3">
                <Sparkles className="h-6 w-6 text-indigo-400" />
              </div>
              <p className="text-sm text-zinc-400 mb-1">
                Ask about your documents
              </p>
              <p className="text-xs text-zinc-600">
                {hasTaxonomy
                  ? "Query the taxonomy, contradictions, and entities"
                  : "Process documents first to enable chat"}
              </p>
            </div>
          )}

          {messages.map((msg, i) => renderMessage(msg, i))}

          {/* Typing indicator */}
          {isTyping && (
            <div className="flex justify-start">
              <div className="rounded-lg bg-zinc-800 px-4 py-3">
                <div className="flex gap-1">
                  <span className="typing-dot h-2 w-2 rounded-full bg-zinc-500" />
                  <span className="typing-dot h-2 w-2 rounded-full bg-zinc-500" />
                  <span className="typing-dot h-2 w-2 rounded-full bg-zinc-500" />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </ScrollArea>

      {/* Suggestions */}
      {messages.length === 0 && (
        <div className="border-t border-zinc-800 px-3 py-2">
          <div className="flex flex-wrap gap-1.5">
            {suggestions.map((q) => (
              <button
                key={q}
                onClick={() => handleSend(q)}
                className="rounded-full border border-zinc-700 bg-zinc-800/50 px-2.5 py-1 text-[10px] text-zinc-400 transition-colors hover:border-indigo-500/30 hover:bg-indigo-500/10 hover:text-indigo-300"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Inline suggestions after last assistant message */}
      {messages.length > 0 &&
        messages[messages.length - 1]?.role === "assistant" &&
        messages[messages.length - 1]?.suggested_queries &&
        (messages[messages.length - 1].suggested_queries?.length ?? 0) > 0 && (
          <div className="border-t border-zinc-800 px-3 py-2">
            <div className="flex flex-wrap gap-1.5">
              {messages[messages.length - 1].suggested_queries!.map((q) => (
                <button
                  key={q}
                  onClick={() => handleSend(q)}
                  className="rounded-full border border-zinc-700 bg-zinc-800/50 px-2.5 py-1 text-[10px] text-zinc-400 transition-colors hover:border-indigo-500/30 hover:bg-indigo-500/10 hover:text-indigo-300"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

      {/* Input */}
      <div className="border-t border-zinc-800 p-3">
        <div className="flex items-center gap-2">
          <input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your documents..."
            className="flex-1 rounded-md border border-zinc-700 bg-zinc-800/50 px-3 py-2 text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            disabled={isTyping}
          />
          <Button
            size="icon"
            onClick={() => handleSend()}
            disabled={!input.trim() || isTyping}
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}
