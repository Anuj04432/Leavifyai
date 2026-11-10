import { useState, useRef, useEffect, FormEvent } from "react";
import {
  Sparkles,
  Send,
  X,
  Calendar,
  Check,
  Loader2,
  CheckCircle2,
  Bot,
  Zap,
  RotateCcw,
} from "lucide-react";
import { api } from "../../lib/api";

interface Message {
  id: string;
  sender: "user" | "bot";
  text: string;
  timestamp: string;
  provider?: string;
  model?: string;
  decision_provider?: string;
  decision_model?: string;
  chat_provider?: string;
  chat_model?: string;
  extracted_leave?: {
    is_leave_request: boolean;
    leave_type?: string;
    policy_id?: string;
    policy_name?: string;
    start_date?: string;
    end_date?: string;
    total_days?: number;
    reason?: string;
    available_balance?: number;
    can_auto_submit?: boolean;
  } | null;
  submitted?: boolean;
}

function getProviderBadge(provider?: string | null, model?: string | null) {
  if (!provider) return null;
  const p = provider.toLowerCase();
  if (p === "omniroute") {
    return { name: "OmniRoute", model: model || "gpt-4o-mini", color: "text-amber-300 border-amber-500/30 bg-amber-500/10" };
  }
  if (p === "openrouter") {
    return { name: "OpenRouter", model: model || "llama-3.3", color: "text-orange-400 border-orange-500/30 bg-orange-500/10" };
  }
  if (p === "gemini") {
    return { name: "Gemini", model: model || "gemini-2.5-flash", color: "text-emerald-400 border-emerald-500/30 bg-emerald-500/10" };
  }
  if (p === "grok") {
    return { name: "Grok", model: model || "grok-2", color: "text-rose-400 border-rose-500/30 bg-rose-500/10" };
  }
  if (p === "local") {
    return { name: "Local LLM", model: model || "llama3", color: "text-amber-400 border-amber-500/30 bg-amber-500/10" };
  }
  return { name: "Deterministic Engine", model: "Rule Engine", color: "text-stone-400 border-stone-700 bg-stone-800/40" };
}

export default function HRAssistantWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [submittingLeaveId, setSubmittingLeaveId] = useState<string | null>(null);
  const [activeDecisionProvider, setActiveDecisionProvider] = useState<string | null>(null);
  const [activeChatProvider, setActiveChatProvider] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "initial-msg",
      sender: "bot",
      text: "Hello! I am your Leavify Copilot. I can check your leave balances, explain company policies, or help you stage and submit time-off requests. Feel free to ask anything or choose a quick suggestion below.",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ]);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isOpen]);

  const handleResetChat = () => {
    setMessages([
      {
        id: "initial-msg",
        sender: "bot",
        text: "Hello! I am your Leavify Copilot. I can check your leave balances, explain company policies, or help you stage and submit time-off requests. Feel free to ask anything or choose a quick suggestion below.",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      },
    ]);
  };

  const handleSendMessage = async (customText?: string) => {
    const textToSend = customText || input.trim();
    if (!textToSend || loading) return;

    const userMsg: Message = {
      id: `user-${Date.now()}`,
      sender: "user",
      text: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!customText) setInput("");
    setLoading(true);

    try {
      const historyPayload = messages.slice(-6).map((m) => ({
        role: m.sender === "user" ? "user" : "assistant",
        content: m.text,
      }));

      const res = await api.post("/agents/chat", {
        message: textToSend,
        history: historyPayload,
      });
      if (res.data.decision_provider || res.data.provider) {
        setActiveDecisionProvider(res.data.decision_provider || res.data.provider);
      }
      if (res.data.chat_provider || res.data.provider) {
        setActiveChatProvider(res.data.chat_provider || res.data.provider);
      }
      const botMsg: Message = {
        id: `bot-${Date.now()}`,
        sender: "bot",
        text: res.data.reply,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        provider: res.data.provider,
        model: res.data.model,
        decision_provider: res.data.decision_provider,
        decision_model: res.data.decision_model,
        chat_provider: res.data.chat_provider,
        chat_model: res.data.chat_model,
        extracted_leave: res.data.extracted_leave,
      };
      setMessages((prev) => [...prev, botMsg]);
    } catch (err: any) {
      const errorMsg: Message = {
        id: `bot-err-${Date.now()}`,
        sender: "bot",
        text: "Sorry, I encountered a temporary connection issue. Please verify your message or check back in a moment.",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleAutoSubmitLeave = async (msgId: string, extracted: NonNullable<Message["extracted_leave"]>) => {
    if (!extracted.policy_id || !extracted.start_date || !extracted.end_date) return;
    try {
      setSubmittingLeaveId(msgId);
      await api.post("/leaves/requests", {
        leave_policy_id: extracted.policy_id,
        start_date: extracted.start_date,
        end_date: extracted.end_date,
        reason: extracted.reason || "Submitted via Leavify Copilot",
      });

      setMessages((prev) =>
        prev.map((m) =>
          m.id === msgId ? { ...m, submitted: true } : m
        )
      );

      setMessages((prev) => [
        ...prev,
        {
          id: `bot-confirm-${Date.now()}`,
          sender: "bot",
          text: `Success! Your request for ${extracted.total_days} day(s) from ${extracted.start_date} to ${extracted.end_date} has been submitted for manager review.`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } catch (err: any) {
      alert(err.response?.data?.detail || "Submission failed.");
    } finally {
      setSubmittingLeaveId(null);
    }
  };

  const starterChips = [
    "Check my balance",
    "Sick leave policy",
    "I need 2 days off next Monday",
    "Annual leave rules",
  ];

  return (
    <aside aria-label="Leavify Copilot Assistant" className="fixed bottom-6 right-6 z-40 font-sans">
      {/* Minimized Launcher Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="px-4 py-3 rounded-full bg-[#181512] hover:bg-[#221d18] text-[#FFFDF8] border border-stone-700 shadow-2xl flex items-center gap-2.5 transition-all motion-reduce:transition-none cursor-pointer group hover:border-orange-500/60 focus-visible:ring-2 focus-visible:ring-orange-500 focus-visible:outline-none"
        >
          <div className="w-7 h-7 rounded-full bg-orange-600 flex items-center justify-center text-white shadow-sm">
            <Sparkles className="w-4 h-4" />
          </div>
          <span className="text-sm font-semibold tracking-tight">Leavify Copilot</span>
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse motion-reduce:animate-none"></span>
        </button>
      )}

      {/* Expanded Floating Chat Drawer */}
      {isOpen && (
        <div className="w-[420px] max-w-[calc(100vw-2rem)] h-[580px] bg-[#181512] border border-stone-800 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
          {/* Header */}
          <div className="p-3.5 bg-[#120f0d] border-b border-stone-800 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-orange-600 flex items-center justify-center font-bold text-white text-xs shadow-sm">
                <Sparkles className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-[#FFFDF8] tracking-tight leading-tight">Leavify Copilot</h3>
                <span className="text-xs text-amber-400/90 flex items-center gap-1.5 font-medium mt-0.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-orange-500 animate-pulse"></span>
                  {activeDecisionProvider
                    ? `Decision: ${getProviderBadge(activeDecisionProvider, null)?.name || activeDecisionProvider} · Chat: ${getProviderBadge(activeChatProvider, null)?.name || 'Active'}`
                    : "Multi-LLM Autonomous Agent"}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-1 text-stone-400">
              <button
                onClick={handleResetChat}
                className="p-1.5 rounded-lg hover:text-white hover:bg-stone-800/80 transition-colors motion-reduce:transition-none cursor-pointer focus-visible:ring-2 focus-visible:ring-orange-500"
                title="Reset conversation"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setIsOpen(false)}
                className="p-1.5 rounded-lg hover:text-white hover:bg-stone-800/80 transition-colors motion-reduce:transition-none cursor-pointer focus-visible:ring-2 focus-visible:ring-orange-500"
                title="Close chat"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Messages Stream */}
          <div className="flex-1 p-4 overflow-y-auto space-y-3.5 text-sm">
            {messages.map((m) => (
              <div
                key={m.id}
                className={`flex gap-2.5 ${m.sender === "user" ? "justify-end" : "justify-start"}`}
              >
                {m.sender === "bot" && (
                  <div className="w-7 h-7 rounded-xl bg-orange-950/70 border border-orange-500/30 flex items-center justify-center shrink-0 mt-0.5 text-orange-400">
                    <Bot className="w-4 h-4" />
                  </div>
                )}

                <div
                  className={`max-w-[85%] rounded-2xl p-3.5 space-y-2.5 ${
                    m.sender === "user"
                      ? "bg-orange-600 text-white rounded-tr-sm shadow-sm"
                      : "bg-[#221d18] border border-stone-800 text-[#F5F2EB]"
                  }`}
                >
                  <p className="leading-relaxed whitespace-pre-wrap text-sm">{m.text}</p>

                  {/* Drafted Leave Card if extracted */}
                  {m.extracted_leave && m.extracted_leave.is_leave_request && (
                    <div className="p-3 rounded-xl bg-[#2b241e] border border-orange-500/30 space-y-2.5 mt-2">
                      <div className="flex items-center justify-between text-xs font-semibold text-orange-400">
                        <span className="flex items-center gap-1.5">
                          <Calendar className="w-3.5 h-3.5 text-orange-400" /> Drafted Application
                        </span>
                        <span className="font-mono text-amber-200/90 text-xs bg-orange-950/60 px-2 py-0.5 rounded border border-orange-500/20">
                          {m.extracted_leave.total_days} business day(s)
                        </span>
                      </div>

                      <div className="text-xs text-stone-300 space-y-1">
                        <div className="flex justify-between">
                          <span className="text-stone-400">Category:</span>
                          <span className="text-white font-medium">{m.extracted_leave.policy_name || "Leave"}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-stone-400">Dates:</span>
                          <span className="text-white font-medium">{m.extracted_leave.start_date} to {m.extracted_leave.end_date}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-stone-400">Available Balance:</span>
                          <span className="text-emerald-400 font-medium">{m.extracted_leave.available_balance ?? "N/A"}d</span>
                        </div>
                      </div>

                      {m.submitted ? (
                        <div className="inline-flex items-center gap-1.5 text-xs text-emerald-400 font-semibold bg-emerald-950/40 border border-emerald-500/30 rounded-lg px-2.5 py-1.5 w-full justify-center">
                          <CheckCircle2 className="w-4 h-4" /> Request Submitted Successfully
                        </div>
                      ) : (
                        <button
                          onClick={() => handleAutoSubmitLeave(m.id, m.extracted_leave!)}
                          disabled={submittingLeaveId === m.id || !m.extracted_leave.can_auto_submit}
                          className="w-full py-2 bg-orange-600 hover:bg-orange-500 active:bg-orange-700 text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-all shadow cursor-pointer disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-orange-500"
                        >
                          {submittingLeaveId === m.id ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin motion-reduce:animate-none" />
                          ) : (
                            <Check className="w-3.5 h-3.5" />
                          )}
                          Confirm & Submit Request
                        </button>
                      )}
                    </div>
                  )}

                  <div className="flex items-center justify-between text-xs opacity-75 pt-1.5 border-t border-stone-800/80 mt-1 gap-1.5 flex-wrap">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      {m.decision_provider && (() => {
                        const b = getProviderBadge(m.decision_provider, m.decision_model);
                        return b ? (
                          <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono border ${b.color}`}>
                            <Zap className="w-2.5 h-2.5" />
                            <span>Decision: {b.name}</span>
                          </span>
                        ) : null;
                      })()}
                      {m.chat_provider && (() => {
                        const b = getProviderBadge(m.chat_provider, m.chat_model);
                        return b ? (
                          <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono border ${b.color}`}>
                            <span>Chat: {b.name}</span>
                          </span>
                        ) : null;
                      })()}
                      {!m.decision_provider && !m.chat_provider && m.provider && (() => {
                        const b = getProviderBadge(m.provider, m.model);
                        return b ? (
                          <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono border ${b.color}`}>
                            <Zap className="w-2.5 h-2.5" />
                            <span>{b.name}</span>
                          </span>
                        ) : null;
                      })()}
                    </div>
                    <span className="text-[11px] text-stone-400 ml-auto font-mono">{m.timestamp}</span>
                  </div>
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex items-center gap-2 text-stone-400 text-sm pl-9">
                <Loader2 className="w-4 h-4 animate-spin text-orange-400 motion-reduce:animate-none" />
                <span className="text-xs">Evaluating policies & drafting response…</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Starter Chips */}
          <div className="px-3.5 py-2 bg-[#14110f] border-t border-stone-800 flex items-center gap-2 overflow-x-auto no-scrollbar">
            {starterChips.map((chip, idx) => (
              <button
                key={idx}
                onClick={() => handleSendMessage(chip)}
                className="px-2.5 py-1 rounded-full bg-[#221d18] hover:bg-[#2e2620] border border-stone-800 hover:border-orange-500/40 text-xs text-stone-300 hover:text-white whitespace-nowrap transition-colors cursor-pointer"
              >
                {chip}
              </button>
            ))}
          </div>

          {/* Input Form */}
          <form
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              handleSendMessage();
            }}
            className="p-3 bg-[#120f0d] border-t border-stone-800 flex items-center gap-2"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask anything or request time off..."
              className="flex-1 bg-[#201b17] border border-stone-800 focus:border-orange-500 focus:ring-1 focus:ring-orange-500/30 rounded-xl px-3.5 py-2.5 text-sm text-[#FFFDF8] placeholder-stone-500 outline-none transition"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="p-2.5 bg-orange-600 hover:bg-orange-500 active:bg-orange-700 text-white rounded-xl transition shadow disabled:opacity-40 cursor-pointer focus-visible:ring-2 focus-visible:ring-orange-500"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      )}
    </aside>
  );
}
