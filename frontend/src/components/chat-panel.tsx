import { useState, useRef, useEffect, useCallback } from "react"
import ReactMarkdown from "react-markdown"
import { cn } from "@/lib/utils"
import type { ChatMessage, CitationType } from "@/lib/types"
import { sendChatMessage } from "@/lib/api"
import { Button } from "./ui/button"
import { ScrollArea } from "./ui/scroll-area"
import { Send, MessageSquare, Sparkles, AlertTriangle, RotateCcw } from "lucide-react"

const CONTRADICTION_PATTERN = /\bnote:\s|contradiction/i

const DEFAULT_SUGGESTIONS = [
  "What document types were detected?",
  "Show me all contradictions",
  "Summarize the taxonomy",
  "Which entities need review?",
]

interface ChatPanelProps {
  hasTaxonomy: boolean
  embedded?: boolean
}

export function ChatPanel({ hasTaxonomy, embedded }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState("")
  const [isTyping, setIsTyping] = useState(false)
  const [suggestions, setSuggestions] = useState<string[]>(DEFAULT_SUGGESTIONS)
  const [sessionId, setSessionId] = useState(() => crypto.randomUUID())
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

  const handleReset = () => {
    setMessages([])
    setSuggestions(DEFAULT_SUGGESTIONS)
    setSessionId(crypto.randomUUID())
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const renderCitation = (citation: CitationType, index: number) => {
    const colorMap = {
      taxonomy: "bg-primary/15 text-primary border-primary/30",
      document: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-300 border-emerald-500/30",
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

  const renderContentWithCallouts = (content: string) => {
    const lines = content.split("\n")
    const segments: { type: "markdown" | "callout"; text: string }[] = []
    let i = 0

    while (i < lines.length) {
      const line = lines[i]

      if (CONTRADICTION_PATTERN.test(line)) {
        const calloutLines: string[] = [line]
        while (
          i + 1 < lines.length &&
          lines[i + 1].trim() !== "" &&
          CONTRADICTION_PATTERN.test(lines[i + 1])
        ) {
          i++
          calloutLines.push(lines[i])
        }
        segments.push({ type: "callout", text: calloutLines.join("\n") })
      } else {
        const last = segments[segments.length - 1]
        if (last && last.type === "markdown") {
          last.text += "\n" + line
        } else {
          segments.push({ type: "markdown", text: line })
        }
      }
      i++
    }

    return segments.map((seg, idx) => {
      if (seg.type === "callout") {
        return (
          <div
            key={idx}
            className="my-1 flex items-start gap-1.5 rounded-r border-l-2 border-warning bg-warning/5 py-1 pl-2 pr-1"
          >
            <AlertTriangle className="mt-0.5 h-3 w-3 flex-shrink-0 text-warning" />
            <span className="text-sm">{seg.text}</span>
          </div>
        )
      }
      return (
        <ReactMarkdown
          key={idx}
          components={{
            p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
            strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
            em: ({ children }) => <em>{children}</em>,
            ul: ({ children }) => <ul className="mb-2 ml-4 list-disc space-y-0.5 last:mb-0">{children}</ul>,
            ol: ({ children }) => <ol className="mb-2 ml-4 list-decimal space-y-0.5 last:mb-0">{children}</ol>,
            li: ({ children }) => <li>{children}</li>,
            h1: ({ children }) => <h1 className="mb-1 text-base font-bold">{children}</h1>,
            h2: ({ children }) => <h2 className="mb-1 text-sm font-bold">{children}</h2>,
            h3: ({ children }) => <h3 className="mb-1 text-sm font-semibold">{children}</h3>,
            code: ({ children, className }) => {
              const isBlock = className?.includes("language-")
              if (isBlock) {
                return (
                  <pre className="my-1 overflow-x-auto rounded bg-background/50 p-2 text-xs">
                    <code>{children}</code>
                  </pre>
                )
              }
              return (
                <code className="rounded bg-background/50 px-1 py-0.5 text-xs font-mono">
                  {children}
                </code>
              )
            },
            pre: ({ children }) => <>{children}</>,
            blockquote: ({ children }) => (
              <blockquote className="my-1 border-l-2 border-primary/30 pl-2 text-muted-foreground">
                {children}
              </blockquote>
            ),
            a: ({ href, children }) => (
              <a href={href} target="_blank" rel="noopener noreferrer" className="text-primary underline">
                {children}
              </a>
            ),
            table: ({ children }) => (
              <div className="my-1 overflow-x-auto">
                <table className="w-full text-xs border-collapse">{children}</table>
              </div>
            ),
            thead: ({ children }) => <thead className="border-b border-border">{children}</thead>,
            th: ({ children }) => <th className="px-2 py-1 text-left font-semibold">{children}</th>,
            td: ({ children }) => <td className="px-2 py-1 border-t border-border/50">{children}</td>,
          }}
        >
          {seg.text}
        </ReactMarkdown>
      )
    })
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
              ? "bg-primary text-primary-foreground"
              : "bg-muted text-foreground"
          )}
        >
          <div className={cn(isUser && "whitespace-pre-wrap")}>
            {isUser ? msg.content : renderContentWithCallouts(msg.content)}
          </div>
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
    <div className={cn(
      "flex h-full flex-col bg-card",
      !embedded && "w-80 border-l border-border"
    )}>
      {!embedded && (
        <div className="border-b border-border p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <MessageSquare className="h-4 w-4 text-primary" />
              <h2 className="text-sm font-semibold text-foreground">Chat</h2>
            </div>
            {messages.length > 0 && (
              <Button
                variant="ghost"
                size="icon"
                onClick={handleReset}
                className="h-7 w-7 text-muted-foreground hover:text-foreground"
                title="Reset chat"
              >
                <RotateCcw className="h-3.5 w-3.5" />
              </Button>
            )}
          </div>
        </div>
      )}

      {/* Messages */}
      <ScrollArea className="flex-1 p-4">
        <div className="space-y-3">
          {messages.length === 0 && (
            <div className="flex flex-col items-center py-8 text-center">
              <div className="rounded-full bg-muted/50 p-3 mb-3">
                <Sparkles className="h-6 w-6 text-primary" />
              </div>
              <p className="text-sm text-muted-foreground mb-1">
                Ask about your documents
              </p>
              <p className="text-xs text-muted-foreground/70">
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
              <div className="rounded-lg bg-muted px-4 py-3">
                <div className="flex gap-1">
                  <span className="typing-dot h-2 w-2 rounded-full bg-muted-foreground" />
                  <span className="typing-dot h-2 w-2 rounded-full bg-muted-foreground" />
                  <span className="typing-dot h-2 w-2 rounded-full bg-muted-foreground" />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </ScrollArea>

      {/* Suggestions */}
      {messages.length === 0 && (
        <div className="border-t border-border px-3 py-2">
          <div className="flex flex-wrap gap-1.5">
            {suggestions.map((q) => (
              <button
                key={q}
                onClick={() => handleSend(q)}
                className="rounded-full border border-border bg-card px-2.5 py-1 text-[10px] text-muted-foreground transition-colors hover:border-primary/30 hover:bg-primary/10 hover:text-primary"
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
          <div className="border-t border-border px-3 py-2">
            <div className="flex flex-wrap gap-1.5">
              {messages[messages.length - 1].suggested_queries!.map((q) => (
                <button
                  key={q}
                  onClick={() => handleSend(q)}
                  className="rounded-full border border-border bg-card px-2.5 py-1 text-[10px] text-muted-foreground transition-colors hover:border-primary/30 hover:bg-primary/10 hover:text-primary"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

      {/* Input */}
      <div className="border-t border-border p-3">
        <div className="flex items-center gap-2">
          {embedded && messages.length > 0 && (
            <Button
              variant="ghost"
              size="icon"
              onClick={handleReset}
              className="h-8 w-8 flex-shrink-0 text-muted-foreground hover:text-foreground"
              title="Reset chat"
            >
              <RotateCcw className="h-3.5 w-3.5" />
            </Button>
          )}
          <input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your documents..."
            className="flex-1 rounded-md border border-border bg-muted/50 px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
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
