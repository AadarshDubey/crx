"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Header } from "@/components/layout";
import { Card, CardContent, Button, Input, Spinner, Badge } from "@/components/ui";
import { ChatMessage, ChatSource } from "@/types";
import { Send, Bot, User, ExternalLink, Sparkles, Search, Database, Zap, CheckCircle, AlertCircle } from "lucide-react";
import { cn, generateId } from "@/lib/utils";
import ReactMarkdown from "react-markdown";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const suggestedQueries = [
  "What is Elon Musk saying?",
  "Latest from WatcherGuru",
  "Summarize CZ's tweets",
  "Michael Saylor's sentiment",
  "Any whale alerts?",
  "Bitcoin sentiment today",
];

interface StreamStatus {
  message: string;
  type: "detecting" | "scraping" | "indexing" | "generating" | "done";
}

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      content:
        "Welcome! I can help you understand crypto market sentiment. Ask about specific influencers like **Elon Musk**, **CZ**, **Saylor**, or **WatcherGuru** and I'll fetch their latest tweets for you!",
      timestamp: new Date(),
    },
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [streamStatus, setStreamStatus] = useState<StreamStatus | null>(null);
  const [statusHistory, setStatusHistory] = useState<string[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamStatus, statusHistory]);

  const getStatusIcon = (message: string) => {
    if (message.includes("Analyzing") || message.includes("Detected")) {
      return <Search size={14} className="text-primary" />;
    }
    if (message.includes("Fetching") || message.includes("Found")) {
      return <Database size={14} className="text-accent" />;
    }
    if (message.includes("Indexed") || message.includes("already")) {
      return <CheckCircle size={14} className="text-bullish" />;
    }
    if (message.includes("Generating")) {
      return <Zap size={14} className="text-warning" />;
    }
    if (message.includes("error") || message.includes("Error") || message.includes("Falling back")) {
      return <AlertCircle size={14} className="text-bearish" />;
    }
    if (message.includes("Using fresh")) {
      return <CheckCircle size={14} className="text-bullish" />;
    }
    return <Spinner size="sm" />;
  };

  const sendMessage = async (content: string) => {
    if (!content.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      id: generateId(),
      role: "user",
      content: content.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");
    setIsLoading(true);
    setStatusHistory([]);
    setStreamStatus(null);

    const assistantId = generateId();
    let fullContent = "";
    let sources: ChatSource[] = [];

    try {
      // Build conversation history
      const conversationHistory = messages
        .filter((m) => m.id !== "welcome")
        .slice(-10) // Last 10 messages
        .map((m) => ({ role: m.role, content: m.content }));

      // Use streaming endpoint
      const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: content.trim(),
          use_context: true,
          conversation_history: conversationHistory,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error("No response body");

      const decoder = new TextDecoder();

      // Add placeholder message
      setMessages((prev) => [
        ...prev,
        {
          id: assistantId,
          role: "assistant",
          content: "",
          timestamp: new Date(),
          isStreaming: true,
        },
      ]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));

              if (data.type === "status") {
                setStreamStatus({ message: data.message, type: "detecting" });
                setStatusHistory((prev) => [...prev, data.message]);
              } else if (data.type === "chunk") {
                fullContent += data.content;
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantId
                      ? { ...m, content: fullContent }
                      : m
                  )
                );
              } else if (data.type === "sources") {
                sources = data.sources || [];
              } else if (data.type === "done") {
                setStreamStatus(null);
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantId
                      ? { ...m, isStreaming: false, sources }
                      : m
                  )
                );
              } else if (data.type === "error") {
                throw new Error(data.message);
              }
            } catch (e) {
              // Ignore parse errors for incomplete chunks
            }
          }
        }
      }
    } catch (error) {
      console.error("Chat error:", error);
      setMessages((prev) => {
        const existing = prev.find((m) => m.id === assistantId);
        if (existing) {
          return prev.map((m) =>
            m.id === assistantId
              ? {
                  ...m,
                  content: "Sorry, I encountered an error. Please try again.",
                  isStreaming: false,
                }
              : m
          );
        }
        return [
          ...prev,
          {
            id: assistantId,
            role: "assistant",
            content: "Sorry, I encountered an error. Please try again.",
            timestamp: new Date(),
            isStreaming: false,
          },
        ];
      });
    } finally {
      setIsLoading(false);
      setStreamStatus(null);
      inputRef.current?.focus();
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(inputValue);
  };

  const handleSuggestionClick = (query: string) => {
    sendMessage(query);
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Header title="AI Analyst" subtitle="Powered by RAG + LLM" showRefresh={false}>
        <Badge variant="default" size="md" className="gap-1.5">
          <Sparkles size={14} />
          Auto-Scraping
        </Badge>
      </Header>

      <div className="flex-1 flex flex-col p-6">
        <Card className="flex-1 flex flex-col overflow-hidden">
          {/* Messages Area */}
          <CardContent className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={cn(
                  "flex gap-3 animate-fade-in",
                  message.role === "user" ? "justify-end" : "justify-start"
                )}
              >
                {message.role === "assistant" && (
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
                    <Bot size={16} className="text-primary" />
                  </div>
                )}

                <div
                  className={cn(
                    "max-w-[70%] rounded-xl px-4 py-3",
                    message.role === "user"
                      ? "bg-primary text-white"
                      : "bg-surface-light text-text-primary"
                  )}
                >
                  {message.isStreaming && !message.content ? (
                    <div className="space-y-2">
                      {statusHistory.map((status, idx) => (
                        <div
                          key={idx}
                          className={cn(
                            "flex items-center gap-2 text-sm",
                            idx === statusHistory.length - 1
                              ? "text-text-primary"
                              : "text-text-muted"
                          )}
                        >
                          {idx === statusHistory.length - 1 ? (
                            getStatusIcon(status)
                          ) : (
                            <CheckCircle size={14} className="text-bullish" />
                          )}
                          <span>{status}</span>
                        </div>
                      ))}
                      {statusHistory.length === 0 && (
                        <div className="flex items-center gap-2">
                          <Spinner size="sm" />
                          <span className="text-text-muted">Processing...</span>
                        </div>
                      )}
                    </div>
                  ) : (
                    <>
                      {/* Status history before response */}
                      {message.isStreaming && statusHistory.length > 0 && (
                        <div className="mb-3 pb-3 border-b border-border space-y-1">
                          {statusHistory.map((status, idx) => (
                            <div
                              key={idx}
                              className="flex items-center gap-2 text-xs text-text-muted"
                            >
                              <CheckCircle size={12} className="text-bullish" />
                              <span>{status}</span>
                            </div>
                          ))}
                        </div>
                      )}
                      
                      <div className="prose prose-invert prose-sm max-w-none">
                        <ReactMarkdown
                          components={{
                            p: ({ children }) => (
                              <p className="mb-2 last:mb-0">{children}</p>
                            ),
                            strong: ({ children }) => (
                              <strong className="text-text-primary font-semibold">
                                {children}
                              </strong>
                            ),
                            ul: ({ children }) => (
                              <ul className="list-disc list-inside mb-2 space-y-1">
                                {children}
                              </ul>
                            ),
                            li: ({ children }) => (
                              <li className="text-text-secondary">{children}</li>
                            ),
                          }}
                        >
                          {message.content}
                        </ReactMarkdown>
                      </div>
                      
                      {/* Typing cursor */}
                      {message.isStreaming && message.content && (
                        <span className="inline-block w-2 h-4 bg-primary animate-pulse ml-1" />
                      )}
                    </>
                  )}

                  {/* Sources */}
                  {message.sources && message.sources.length > 0 && !message.isStreaming && (
                    <div className="mt-3 pt-3 border-t border-border">
                      <p className="text-xs text-text-muted mb-2">Sources:</p>
                      <div className="space-y-1">
                        {message.sources.slice(0, 3).map((source, idx) => (
                          <div
                            key={idx}
                            className="flex items-start gap-2 text-xs text-text-secondary"
                          >
                            <span className="text-text-muted">└</span>
                            <span className="line-clamp-1 flex-1">
                              {source.source_type === "tweet" ? "@" : ""}
                              {source.content.slice(0, 60)}...
                            </span>
                            {source.url && (
                              <a
                                href={source.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-primary hover:text-primary-hover flex-shrink-0"
                              >
                                <ExternalLink size={12} />
                              </a>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {message.role === "user" && (
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-surface-light flex items-center justify-center">
                    <User size={16} className="text-text-secondary" />
                  </div>
                )}
              </div>
            ))}
            <div ref={messagesEndRef} />
          </CardContent>

          {/* Suggested Queries */}
          {messages.length <= 2 && !isLoading && (
            <div className="px-4 py-3 border-t border-border">
              <p className="text-xs text-text-muted mb-2">Try asking about:</p>
              <div className="flex flex-wrap gap-2">
                {suggestedQueries.map((query) => (
                  <button
                    key={query}
                    onClick={() => handleSuggestionClick(query)}
                    className={cn(
                      "px-3 py-1.5 rounded-full text-xs",
                      "bg-surface-light text-text-secondary",
                      "hover:bg-border hover:text-text-primary",
                      "transition-colors"
                    )}
                  >
                    {query}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Input Area */}
          <form onSubmit={handleSubmit} className="p-4 border-t border-border">
            <div className="flex gap-3">
              <Input
                ref={inputRef}
                placeholder="Ask about crypto sentiment or specific influencers..."
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                disabled={isLoading}
                className="flex-1"
              />
              <Button
                type="submit"
                disabled={!inputValue.trim() || isLoading}
                className="px-6"
              >
                {isLoading ? <Spinner size="sm" /> : <Send size={18} />}
              </Button>
            </div>
          </form>
        </Card>
      </div>
    </div>
  );
}
