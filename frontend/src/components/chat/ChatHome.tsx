import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useChatStore } from "../../stores/chatStore";
import {
  createConversation,
  listReviews,
  triggerMorningBrief,
  ApiError,
} from "../../api/client";
import { useErrorStore } from "../../stores/errorStore";

const BRIEF_CACHE_KEY = "morning_brief_cache";

export default function ChatHome() {
  const navigate = useNavigate();
  const conversations = useChatStore((s) => s.conversations);
  const addConversation = useChatStore((s) => s.addConversation);
  const setActiveConversation = useChatStore((s) => s.setActiveConversation);
  const addError = useErrorStore((s) => s.addError);
  const [brief, setBrief] = useState<string | null>(null);
  const [loadingBrief, setLoadingBrief] = useState(false);

  const greeting = (() => {
    const h = new Date().getHours();
    if (h < 12) return "早上好";
    if (h < 18) return "下午好";
    return "晚上好";
  })();

  const today = new Date().toLocaleDateString("zh-CN", {
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "long",
  });

  useEffect(() => {
    const cached = localStorage.getItem(BRIEF_CACHE_KEY);
    if (cached) {
      try {
        const { content, date } = JSON.parse(cached);
        if (date === new Date().toISOString().slice(0, 10)) {
          setBrief(content);
          return;
        }
      } catch {
        // ignore
      }
    }
    loadBriefFromReviews();
  }, []);

  const loadBriefFromReviews = async () => {
    try {
      const reviews = await listReviews(5);
      const morning = reviews.find((r) => r.type === "morning");
      if (morning?.content) {
        setBrief(morning.content.slice(0, 300));
      }
    } catch {
      // optional
    }
  };

  const handleRefreshBrief = async () => {
    setLoadingBrief(true);
    try {
      const res = await triggerMorningBrief();
      const content =
        typeof res.result === "string"
          ? res.result
          : (res.result as { content?: string })?.content || "简报已生成";
      setBrief(content.slice(0, 300));
      localStorage.setItem(
        BRIEF_CACHE_KEY,
        JSON.stringify({ content, date: new Date().toISOString().slice(0, 10) })
      );
    } catch (err) {
      const msg =
        err instanceof ApiError ? err.message : "生成简报失败";
      addError(msg, "简报");
    } finally {
      setLoadingBrief(false);
    }
  };

  const handleNewChat = async () => {
    try {
      const conv = await createConversation();
      addConversation(conv);
      setActiveConversation(conv.id);
      navigate(`/chat/${conv.id}`);
    } catch (err) {
      const msg =
        err instanceof ApiError ? err.message : "创建对话失败";
      addError(msg, "对话");
    }
  };

  const shortcuts = [
    { label: "查看收件箱", path: "/inbox" },
    { label: "查看停滞目标", path: "/goals" },
    { label: "新建目标", path: "/goals" },
  ];

  const recent = conversations.slice(0, 3);

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-2xl mx-auto space-y-8">
        <div className="text-center pt-8">
          <div className="text-5xl mb-4">🧠</div>
          <h2 className="text-2xl font-semibold text-gray-200">
            {greeting}，欢迎回来
          </h2>
          <p className="text-gray-500 mt-2">{today}</p>
        </div>

        {brief && (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-emerald-400">今日简报</h3>
              <button
                onClick={handleRefreshBrief}
                disabled={loadingBrief}
                className="text-xs text-gray-500 hover:text-gray-300"
              >
                {loadingBrief ? "生成中…" : "刷新"}
              </button>
            </div>
            <p className="text-sm text-gray-400 whitespace-pre-wrap line-clamp-4">
              {brief}
            </p>
          </div>
        )}

        {!brief && (
          <div className="text-center">
            <button
              onClick={handleRefreshBrief}
              disabled={loadingBrief}
              className="text-sm text-emerald-500 hover:text-emerald-400"
            >
              {loadingBrief ? "正在生成今日简报…" : "生成今日简报"}
            </button>
          </div>
        )}

        <div className="grid grid-cols-3 gap-3">
          {shortcuts.map((s) => (
            <button
              key={s.label}
              onClick={() => navigate(s.path)}
              className="p-4 bg-gray-900 border border-gray-800 rounded-xl hover:border-emerald-600/50 transition-colors text-sm text-gray-300"
            >
              {s.label}
            </button>
          ))}
        </div>

        {recent.length > 0 && (
          <div>
            <h3 className="text-sm font-medium text-gray-400 mb-3">最近对话</h3>
            <div className="space-y-2">
              {recent.map((conv) => (
                <button
                  key={conv.id}
                  onClick={() => {
                    setActiveConversation(conv.id);
                    navigate(`/chat/${conv.id}`);
                  }}
                  className="w-full text-left px-4 py-3 bg-gray-900 border border-gray-800 rounded-xl hover:bg-gray-800/50 transition-colors"
                >
                  <span className="text-sm text-gray-200">
                    {conv.title || "新对话"}
                  </span>
                  {conv.summary && (
                    <p className="text-xs text-gray-500 mt-1 line-clamp-1">
                      {conv.summary}
                    </p>
                  )}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="text-center pb-8">
          <button
            onClick={handleNewChat}
            className="px-6 py-3 bg-emerald-600 hover:bg-emerald-700 rounded-xl text-white font-medium transition-colors"
          >
            开始新对话
          </button>
        </div>
      </div>
    </div>
  );
}
