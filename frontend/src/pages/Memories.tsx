import { useEffect, useState } from "react";
import { listMemoriesGrouped, type MemoryRow } from "../api/client";

export default function MemoriesPage() {
  const [memories, setMemories] = useState<MemoryRow[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const grouped = await listMemoriesGrouped();
      setMemories(grouped.memories);
    } catch {
      // backend offline
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-500">加载中…</div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-3xl mx-auto space-y-8">
        <div>
          <h2 className="text-2xl font-bold mb-2">记忆</h2>
          <p className="text-sm text-gray-500">
            系统从对话与活动中提取的长期记忆。
          </p>
        </div>

        <section>
          {memories.length === 0 ? (
            <p className="text-gray-600 text-sm">暂无记忆。</p>
          ) : (
            <ul className="space-y-2">
              {memories.map((m) => (
                <li
                  key={m.id}
                  className="bg-gray-900 border border-gray-800 rounded-lg p-3 text-sm"
                >
                  <p className="text-gray-300">{m.content}</p>
                  {m.confidence != null && (
                    <p className="text-xs text-gray-500 mt-1">
                      置信度 {m.confidence.toFixed(2)}
                      {m.category ? ` · ${m.category}` : ""}
                    </p>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}
