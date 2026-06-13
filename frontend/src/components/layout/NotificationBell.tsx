import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bell } from "lucide-react";
import { listNotifications, type Notification } from "../../api/client";

export default function NotificationBell() {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>([]);

  useEffect(() => {
    loadNotifications();
    const interval = setInterval(loadNotifications, 60000);
    return () => clearInterval(interval);
  }, []);

  const loadNotifications = async () => {
    try {
      const items = await listNotifications(15);
      setNotifications(items);
    } catch {
      // optional
    }
  };

  const unread = notifications.filter((n) => n.read === 0 || n.read === undefined).length;

  const handleClick = (n: Notification) => {
    setOpen(false);
    if (n.type === "goal_stagnant" || n.type.includes("goal")) {
      navigate("/goals");
    } else if (n.type.includes("brief") || n.type.includes("review")) {
      navigate("/");
    } else if (n.type.includes("inbox") || n.type.includes("email")) {
      navigate("/inbox");
    } else {
      navigate("/dashboard");
    }
  };

  return (
    <div className="relative px-3 pb-2">
      <button
        onClick={() => {
          setOpen(!open);
          if (!open) loadNotifications();
        }}
        className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-gray-400 hover:bg-gray-800/50 transition-colors"
        aria-label="通知"
      >
        <Bell size={18} />
        <span>通知</span>
        {unread > 0 && (
          <span className="ml-auto bg-emerald-600 text-white text-xs px-1.5 py-0.5 rounded-full min-w-[20px] text-center">
            {unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute bottom-full left-2 right-2 mb-1 bg-gray-900 border border-gray-700 rounded-xl shadow-xl max-h-64 overflow-y-auto z-50">
          {notifications.length === 0 ? (
            <p className="text-xs text-gray-500 p-4 text-center">暂无通知</p>
          ) : (
            notifications.map((n) => (
              <button
                key={n.id}
                onClick={() => handleClick(n)}
                className="w-full text-left p-3 hover:bg-gray-800 border-b border-gray-800 last:border-0"
              >
                <p className="text-sm text-emerald-400">{n.title}</p>
                <p className="text-xs text-gray-500 mt-1 line-clamp-2">
                  {n.content}
                </p>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
