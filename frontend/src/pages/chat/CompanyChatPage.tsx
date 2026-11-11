import { useState, useRef, useEffect, FormEvent } from "react";
import {
  Sparkles,
  Send,
  RotateCcw,
  Loader2,
  Check,
  CheckCircle2,
  Bot,
  User,
  Zap,
  Calendar,
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
    start_date?: string;
    end_date?: string;
    reason?: string;
    can_auto_submit?: boolean;
    auto_submitted?: boolean;
  };
}

export default function CompanyChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "initial-msg",
      sender: "bot",
      text: "Welcome to Talk with Company! I am your Leavify.ai intelligence copilot. You can ask me anything about official company guidelines, check your personalized leave balances, learn about remote work rules, or draft and submit time-off requests directly in plain English.",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ]);

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [submittingLeaveId, setSubmittingLeaveId] = useState<string | null>(null);
  const [activeDecisionProvider, setActiveDecisionProvider] = useState<string | null>(null);
  const [activeChatProvider, setActiveChatProvider] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const starterChips = [
    "Check my leave balances",
    "What is the notice period for casual leave?",
    "Can I take 2 days off next Monday and Tuesday?",
    "Explain our annual leave carry-forward policy",
    "How does sick leave certification work?",
  ];

  const handleResetChat = () => {
    setMessages([
      {
        id: "initial-msg",
        sender: "bot",
        text: "Welcome to Talk with Company! I am your Leavify.ai intelligence copilot. You can ask me anything about official company guidelines, check your personalized leave balances, learn about remote work rules, or draft and submit time-off requests directly in plain English.",
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
      const historyPayload = messages.slice(-8).map((m) => ({
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
      setMessages((prev) => [
        ...prev,
        {
          id: `bot-err-${Date.now()}`,
          sender: "bot",
          text: "I'm having difficulty connecting to the knowledge engine right now. Please try again shortly.",
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleAutoSubmitLeave = async (msgId: string, leaveData: any) => {
    try {
      setSubmittingLeaveId(msgId);
      const policiesRes = await api.get("/leaves/policies");
      const policies = policiesRes.data;

      let targetPolicy = policies[0];
      if (leaveData.leave_type) {
        const match = policies.find(
          (p: any) => p.leave_type.toLowerCase() === leaveData.leave_type.toLowerCase()
        );
        if (match) targetPolicy = match;
      }

      await api.post("/leaves/requests", {
        leave_policy_id: targetPolicy?.id || policies[0]?.id,
        policy_id: targetPolicy?.id || policies[0]?.id,
        start_date: leaveData.start_date,
        end_date: leaveData.end_date,
        reason: leaveData.reason || "Time off request via Leavify Company Copilot",
      });

      setMessages((prev) =>
        prev.map((m) => {
          if (m.id === msgId && m.extracted_leave) {
            return {
              ...m,
              extracted_leave: { ...m.extracted_leave, auto_submitted: true },
            };
          }
          return m;
        })
      );

      setMessages((prev) => [
        ...prev,
        {
          id: `bot-confirm-${Date.now()}`,
          sender: "bot",
          text: `Your ${targetPolicy?.name || "Leave"} application from ${leaveData.start_date} to ${leaveData.end_date} has been officially recorded and queued in the Approval Cockpit.`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      const errorMsg =
        typeof detail === "string"
          ? detail
          : Array.isArray(detail)
          ? detail.map((d: any) => d.msg || JSON.stringify(d)).join(", ")
          : typeof detail === "object" && detail !== null
          ? JSON.stringify(detail)
          : "Leave submission failed. Please check policy balance or dates.";

      setMessages((prev) => [
        ...prev,
        {
          id: `bot-err-${Date.now()}`,
          sender: "bot",
          text: `⚠️ Leave submission could not be completed: ${errorMsg}`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } finally {
      setSubmittingLeaveId(null);
    }
  };

  return (
    <div className="flex-1 flex flex-col h-[calc(100vh-3.5rem)] md:h-screen bg-[#0c0a09] text-stone-100">
      {/* Top Console Header */}
      <div className="px-6 py-4 bg-[#141210] border-b border-stone-800 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-orange-600 flex items-center justify-center font-bold text-white shadow-sm">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-base sm:text-lg font-bold text-[#FFFDF8] tracking-tight leading-tight flex items-center gap-2">
              <span>Talk with Company</span>
              <span className="text-xs px-2 py-0.5 rounded-md bg-orange-950/60 border border-orange-500/30 text-orange-400 font-mono font-medium">
                Leavify Intelligence
              </span>
            </h1>
            <p className="text-xs text-stone-400 mt-0.5">
              Organizational knowledge base, employee policies, and automated leave staging.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {(activeDecisionProvider || activeChatProvider) && (
            <div className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[#1c1917] border border-stone-800 text-xs font-mono text-stone-300">
              <Zap className="w-3 h-3 text-orange-400" />
              <span>
                {activeDecisionProvider ? `Decision: ${activeDecisionProvider}` : ""}
                {activeDecisionProvider && activeChatProvider ? " · " : ""}
                {activeChatProvider ? `Chat: ${activeChatProvider}` : ""}
              </span>
            </div>
          )}

          <button
            onClick={handleResetChat}
            className="px-3 py-1.5 rounded-xl bg-[#1c1917] hover:bg-[#25201c] border border-stone-800 text-xs text-stone-300 hover:text-white flex items-center gap-1.5 transition cursor-pointer"
            title="Start new conversation"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Reset Thread</span>
          </button>
        </div>
      </div>

      {/* Main Messages Viewport */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 max-w-4xl mx-auto w-full">
        {messages.map((m) => (
          <div
            key={m.id}
            className={`flex items-start gap-3.5 ${
              m.sender === "user" ? "flex-row-reverse" : "flex-row"
            }`}
          >
            {/* Avatar */}
            <div
              className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 text-sm font-semibold shadow-sm ${
                m.sender === "user"
                  ? "bg-orange-600 text-white"
                  : "bg-[#1c1917] border border-stone-700 text-orange-400"
              }`}
            >
              {m.sender === "user" ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
            </div>

            {/* Bubble */}
            <div
              className={`max-w-[85%] sm:max-w-xl rounded-2xl p-4 shadow-sm space-y-2.5 ${
                m.sender === "user"
                  ? "bg-orange-600 text-white rounded-tr-xs"
                  : "bg-[#141210] border border-stone-800 text-stone-200 rounded-tl-xs"
              }`}
            >
              <p className="text-sm sm:text-base leading-relaxed whitespace-pre-wrap font-sans">
                {m.text}
              </p>

              {/* Extracted Leave Proposal Card */}
              {m.extracted_leave && m.extracted_leave.is_leave_request && (
                <div className="mt-3 p-3.5 rounded-xl bg-[#1c1917] border border-orange-500/30 space-y-2.5">
                  <div className="flex items-center justify-between text-xs text-orange-400 font-semibold">
                    <span className="flex items-center gap-1.5">
                      <Calendar className="w-3.5 h-3.5" />
                      Detected Leave Application
                    </span>
                    <span className="font-mono uppercase text-[10px] px-2 py-0.5 rounded bg-orange-950/60 border border-orange-500/20">
                      {m.extracted_leave.leave_type || "General Leave"}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-xs text-stone-300">
                    <div>
                      <span className="text-stone-500 text-[11px] block">Start Date</span>
                      <span className="font-mono text-white">{m.extracted_leave.start_date || "—"}</span>
                    </div>
                    <div>
                      <span className="text-stone-500 text-[11px] block">End Date</span>
                      <span className="font-mono text-white">{m.extracted_leave.end_date || "—"}</span>
                    </div>
                  </div>

                  {m.extracted_leave.reason && (
                    <div className="text-xs text-stone-300">
                      <span className="text-stone-500 text-[11px] block">Reason</span>
                      <span className="italic">{m.extracted_leave.reason}</span>
                    </div>
                  )}

                  {m.extracted_leave.auto_submitted ? (
                    <div className="flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg bg-emerald-950/50 border border-emerald-500/30 text-emerald-400 text-xs font-semibold">
                      <CheckCircle2 className="w-4 h-4" />
                      Leave Request Submitted to Approval Cockpit
                    </div>
                  ) : (
                    <button
                      type="button"
                      onClick={() => handleAutoSubmitLeave(m.id, m.extracted_leave!)}
                      disabled={submittingLeaveId === m.id}
                      className="w-full py-2.5 px-4 bg-orange-600 hover:bg-orange-500 active:bg-orange-700 text-white rounded-xl text-xs font-semibold flex items-center justify-center gap-2 transition shadow cursor-pointer disabled:opacity-50"
                    >
                      {submittingLeaveId === m.id ? (
                        <>
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          <span>Submitting Application…</span>
                        </>
                      ) : (
                        <>
                          <Check className="w-3.5 h-3.5" />
                          <span>Confirm & Submit Application</span>
                        </>
                      )}
                    </button>
                  )}
                </div>
              )}

              {/* Timestamp & Model Metadata */}
              <div
                className={`flex items-center justify-between text-[11px] font-mono pt-1 ${
                  m.sender === "user" ? "text-orange-200" : "text-stone-500"
                }`}
              >
                <span>{m.timestamp}</span>
                {m.decision_provider && <span>Engine: {m.decision_provider}</span>}
              </div>
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex items-center gap-3 text-stone-400 pl-2">
            <div className="w-9 h-9 rounded-xl bg-[#1c1917] border border-stone-800 text-orange-400 flex items-center justify-center">
              <Bot className="w-4 h-4" />
            </div>
            <div className="flex items-center gap-2 text-sm bg-[#141210] border border-stone-800 px-4 py-2.5 rounded-2xl">
              <Loader2 className="w-4 h-4 animate-spin text-orange-500" />
              <span>Analyzing company knowledge base & policy vectors…</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Topic Chips */}
      <div className="px-4 sm:px-6 py-2.5 bg-[#120f0d] border-t border-stone-800/80 max-w-4xl mx-auto w-full">
        <div className="flex items-center gap-2 overflow-x-auto no-scrollbar">
          {starterChips.map((chip, idx) => (
            <button
              key={idx}
              onClick={() => handleSendMessage(chip)}
              className="px-3 py-1.5 rounded-full bg-[#1c1917] hover:bg-[#25201c] border border-stone-800 hover:border-orange-500/40 text-xs text-stone-300 hover:text-white whitespace-nowrap transition cursor-pointer shrink-0"
            >
              {chip}
            </button>
          ))}
        </div>
      </div>

      {/* Bottom Message Input Bar */}
      <div className="p-4 sm:p-6 bg-[#141210] border-t border-stone-800 shrink-0">
        <form
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            handleSendMessage();
          }}
          className="max-w-4xl mx-auto flex items-center gap-3"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about company rules, check personal leave entitlement, or type a request..."
            className="flex-1 bg-[#1a1714] border border-stone-800 focus:border-orange-500 focus:ring-1 focus:ring-orange-500/30 rounded-2xl px-4 py-3 text-sm text-[#FFFDF8] placeholder-stone-500 outline-none transition"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-5 py-3 bg-orange-600 hover:bg-orange-500 active:bg-orange-700 text-white rounded-2xl text-sm font-semibold flex items-center gap-2 transition shadow disabled:opacity-40 cursor-pointer shrink-0"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            <span className="hidden sm:inline">Send</span>
          </button>
        </form>
      </div>
    </div>
  );
}
