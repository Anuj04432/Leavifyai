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
} from "lucide-react";
import { api } from "../../lib/api";

interface Message {
  id: string;
  sender: "user" | "bot";
  text: string;
  timestamp: string;
  provider?: string;
  model?: string;
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
    return { name: "OmniRoute", model: model || "gpt-4o-mini", color: "text-amber-400 border-amber-500/30 bg-amber-500/10" };
  }
  if (p === "openrouter") {
    return { name: "OpenRouter", model: model || "llama-3.3", color: "text-cyan-400 border-cyan-500/30 bg-cyan-500/10" };
  }
  if (p === "gemini") {
    return { name: "Gemini", model: model || "gemini-2.5-flash", color: "text-emerald-400 border-emerald-500/30 bg-emerald-500/10" };
  }
  if (p === "grok") {
    return { name: "Grok", model: model || "grok-2", color: "text-rose-400 border-rose-500/30 bg-rose-500/10" };
  }
  if (p === "local") {
    return { name: "Local LLM", model: model || "llama3", color: "text-indigo-400 border-indigo-500/30 bg-indigo-500/10" };
  }
  return { name: "Deterministic Engine", model: "Rule Engine", color: "text-slate-400 border-slate-700 bg-slate-800/40" };
}

export default function HRAssistantWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [submittingLeaveId, setSubmittingLeaveId] = useState<string | null>(null);
  const [activeProvider, setActiveProvider] = useState<string | null>(null);
  const [activeModel, setActiveModel] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "initial-msg",
      sender: "bot",
      text: "Hi! I am your WorkforceAI Supervisor powered by our Multi-Provider Fallback Router (OmniRoute, OpenRouter, Gemini, Grok, Local, & In-House Engine). You can ask me about your leave balances, company policies, or type something like 'I need next Monday off for personal reasons' to draft a request.",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ]);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isOpen]);

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
      const res = await api.post("/agents/chat", { message: textToSend });
      if (res.data.provider) {
        setActiveProvider(res.data.provider);
        setActiveModel(res.data.model);
      }
      const botMsg: Message = {
        id: `bot-${Date.now()}`,
        sender: "bot",
        text: res.data.reply,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        provider: res.data.provider,
        model: res.data.model,
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
        reason: extracted.reason || "Submitted via WorkforceAI Copilot",
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
    "I need 2 days off next Monday",
    "What is our sick leave policy?",
  ];

  return (
    <aside aria-label="WorkforceAI Copilot Assistant" className="fixed bottom-6 right-6 z-40 font-sans">
      {/* Minimized Launcher Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="px-4 py-2.5 rounded-full bg-slate-900 hover:bg-slate-800 text-white border border-slate-700 flex items-center gap-2.5 transition-colors motion-reduce:transition-none cursor-pointer group focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none"
        >
          <div className="w-6 h-6 rounded-full bg-indigo-600 flex items-center justify-center">
            <Sparkles className="w-3.5 h-3.5 text-white" />
          </div>
          <span className="text-xs font-semibold">WorkforceAI Copilot</span>
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse motion-reduce:animate-none"></span>
        </button>
      )}

      {/* Expanded Floating Chat Drawer */}
      {isOpen && (
        <div className="w-96 max-w-[calc(100vw-2rem)] h-[520px] bg-slate-900 border border-slate-800 rounded-2xl flex flex-col overflow-hidden">
          {/* Header */}
          <div className="p-3.5 bg-slate-950 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-lg bg-indigo-600 flex items-center justify-center font-bold text-white text-xs">
                <Sparkles className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-xs font-bold text-white leading-tight">WorkforceAI Copilot</h3>
                <span className="text-[11px] text-emerald-400 flex items-center gap-1 font-medium">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                  {activeProvider
                    ? `${getProviderBadge(activeProvider, activeModel)?.name || activeProvider} (${activeModel || 'Active'})`
                    : "Multi-LLM Fallback Engine"}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-1">
              <button
                onClick={() => setIsOpen(false)}
                className="p-1 rounded text-slate-400 hover:text-white transition-colors motion-reduce:transition-none cursor-pointer focus-visible:ring-2 focus-visible:ring-indigo-500"
                title="Close chat"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Messages Stream */}
          <div className="flex-1 p-3.5 overflow-y-auto space-y-3 text-xs">
            {messages.map((m) => (
              <div
                key={m.id}
                className={`flex gap-2 ${m.sender === "user" ? "justify-end" : "justify-start"}`}
              >
                {m.sender === "bot" && (
                  <div className="w-6 h-6 rounded-full bg-indigo-600/30 border border-indigo-500/30 flex items-center justify-center shrink-0 mt-0.5">
                    <Bot className="w-3.5 h-3.5 text-indigo-400" />
                  </div>
                )}

                <div
                  className={`max-w-[85%] rounded-xl p-3 space-y-2 ${
                    m.sender === "user"
                      ? "bg-indigo-600 text-white"
                      : "bg-slate-950 border border-slate-800 text-slate-200"
                  }`}
                >
                  <p className="leading-relaxed whitespace-pre-wrap">{m.text}</p>

                  {/* Drafted Leave Card if extracted */}
                  {m.extracted_leave && m.extracted_leave.is_leave_request && (
                    <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800 space-y-2 mt-2">
                      <div className="flex items-center justify-between text-[11px] font-semibold text-indigo-400">
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3 h-3" /> Drafted Application
                        </span>
                        <span className="font-mono text-slate-300">
                          {m.extracted_leave.total_days} business day(s)
                        </span>
                      </div>

                      <div className="text-xs text-slate-400 space-y-0.5">
                        <div>Category: <span className="text-white">{m.extracted_leave.policy_name || "Leave"}</span></div>
                        <div>Dates: <span className="text-white">{m.extracted_leave.start_date} to {m.extracted_leave.end_date}</span></div>
                        <div>Available: <span className="text-emerald-400">{m.extracted_leave.available_balance}d</span></div>
                      </div>

                      {m.submitted ? (
                        <div className="inline-flex items-center gap-1 text-xs text-emerald-400 font-semibold">
                          <CheckCircle2 className="w-3.5 h-3.5" /> Request Submitted
                        </div>
                      ) : (
                        <button
                          onClick={() => handleAutoSubmitLeave(m.id, m.extracted_leave!)}
                          disabled={submittingLeaveId === m.id || !m.extracted_leave.can_auto_submit}
                          className="w-full py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors motion-reduce:transition-none cursor-pointer disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-indigo-500"
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

                  <div className="flex items-center justify-between text-[10px] opacity-70 pt-1 border-t border-slate-800/60 mt-1">
                    {m.provider ? (
                      (() => {
                        const b = getProviderBadge(m.provider, m.model);
                        return b ? (
                          <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono border ${b.color}`}>
                            <Zap className="w-2.5 h-2.5" />
                            <span>{b.name}</span>
                          </span>
                        ) : <span />;
                      })()
                    ) : <span />}
                    <span>{m.timestamp}</span>
                  </div>
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex items-center gap-2 text-slate-400 text-xs pl-8">
                <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-400 motion-reduce:animate-none" />
                <span className="text-xs">Supervisor evaluating policies…</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Starter Chips */}
          <div className="px-3 py-1.5 bg-slate-950/80 border-t border-slate-800/80 flex items-center gap-1.5 overflow-x-auto no-scrollbar">
            {starterChips.map((chip, idx) => (
              <button
                key={idx}
                onClick={() => handleSendMessage(chip)}
                className="px-2 py-0.5 rounded-full bg-slate-900 hover:bg-slate-800 border border-slate-800 text-[10px] text-slate-400 hover:text-slate-200 whitespace-nowrap transition cursor-pointer"
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
            className="p-2.5 bg-slate-950 border-t border-slate-800 flex items-center gap-2"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask anything or request time off..."
              className="flex-1 bg-slate-900 border border-slate-800 focus:border-indigo-500 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 outline-none transition"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="p-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition disabled:opacity-40 cursor-pointer"
            >
              <Send className="w-3.5 h-3.5" />
            </button>
          </form>
        </div>
      )}
    </aside>
  );
}
