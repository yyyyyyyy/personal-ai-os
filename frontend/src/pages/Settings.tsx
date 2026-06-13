import { useEffect, useState } from "react";
import {
  getSystemHealth,
  fetchSystemInfo,
  getLlmProviders,
  getMcpStatus,
  exportData,
  importData,
  listInboxEmails,
  ApiError,
  type HealthResponse,
  type SystemInfo,
  type LlmProvidersResponse,
  type McpStatusResponse,
} from "../api/client";
import { useErrorStore } from "../stores/errorStore";
import Card from "../components/ui/Card";
import Button from "../components/ui/Button";
import Badge from "../components/ui/Badge";
import { Input } from "../components/ui/Input";
import Spinner from "../components/ui/Spinner";

const STATUS_LABELS: Record<string, string> = {
  connected: "已连接",
  lazy: "懒加载",
  disconnected: "未连接",
  unavailable: "不可用",
};

const STATUS_TONE: Record<string, "success" | "warning" | "danger" | "default"> = {
  connected: "success",
  lazy: "warning",
  disconnected: "default",
  unavailable: "danger",
};

export default function SettingsPage() {
  const addError = useErrorStore((s) => s.addError);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [info, setInfo] = useState<SystemInfo | null>(null);
  const [llm, setLlm] = useState<LlmProvidersResponse | null>(null);
  const [mcp, setMcp] = useState<McpStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [importing, setImporting] = useState(false);
  const [importConfirm, setImportConfirm] = useState("");
  const [emailStatus, setEmailStatus] = useState<
    "unknown" | "ok" | "not_configured" | "error"
  >("unknown");

  const checkEmailStatus = async () => {
    try {
      await listInboxEmails();
      setEmailStatus("ok");
    } catch (err) {
      const msg = err instanceof ApiError ? err.message.toLowerCase() : "";
      if (
        msg.includes("email") ||
        msg.includes("imap") ||
        msg.includes("not configured")
      ) {
        setEmailStatus("not_configured");
      } else {
        setEmailStatus("error");
      }
    }
  };

  const load = async () => {
    setLoading(true);
    try {
      const [h, i, l, m] = await Promise.all([
        getSystemHealth(),
        fetchSystemInfo(),
        getLlmProviders(),
        getMcpStatus(),
      ]);
      setHealth(h);
      setInfo(i);
      setLlm(l);
      setMcp(m);
      await checkEmailStatus();
    } catch (err) {
      const msg =
        err instanceof ApiError ? err.message : "加载设置失败";
      addError(msg, "设置");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleExport = async () => {
    setExporting(true);
    try {
      const data = await exportData();
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `personal-ai-backup-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      const msg =
        err instanceof ApiError ? err.message : "导出失败";
      addError(msg, "设置");
    } finally {
      setExporting(false);
    }
  };

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImporting(true);
    try {
      const text = await file.text();
      const data = JSON.parse(text);
      const writeImport = importConfirm === "DESTROY_AND_IMPORT";
      await importData(data, !writeImport);
      if (writeImport) setImportConfirm("");
      await load();
    } catch (err) {
      const msg =
        err instanceof ApiError ? err.message : "导入失败";
      addError(msg, "设置");
    } finally {
      setImporting(false);
      e.target.value = "";
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center gap-2 text-gray-500">
        <Spinner />
        加载设置…
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-3xl mx-auto space-y-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-100">设置</h2>
          <p className="text-sm text-gray-500 mt-1">
            系统状态、LLM 配置与数据主权管理
          </p>
        </div>

        <Card>
          <h3 className="text-sm font-medium text-gray-300 mb-3">系统状态</h3>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-500">版本</span>
              <p className="text-gray-200">{health?.version}</p>
            </div>
            <div>
              <span className="text-gray-500">认证</span>
              <p className="text-gray-200">
                {health?.auth_required ? "已启用" : "未启用"}
              </p>
            </div>
            <div>
              <span className="text-gray-500">对话</span>
              <p className="text-gray-200">{info?.conversations ?? 0}</p>
            </div>
            <div>
              <span className="text-gray-500">目标 / 记忆</span>
              <p className="text-gray-200">
                {info?.goals ?? 0} / {info?.memories ?? 0}
              </p>
            </div>
          </div>
        </Card>

        <Card>
          <h3 className="text-sm font-medium text-gray-300 mb-3">LLM 配置</h3>
          <p className="text-xs text-gray-500 mb-2">
            默认模型：{llm?.default || "—"}
          </p>
          <div className="space-y-1">
            {(llm?.providers || []).map((p) => (
              <div
                key={p.name}
                className="flex items-center justify-between text-sm py-1"
              >
                <span className="text-gray-300">{p.name}</span>
                <Badge tone={p.available !== false ? "success" : "danger"}>
                  {p.available !== false ? "可用" : "不可用"}
                </Badge>
              </div>
            ))}
          </div>
          <p className="text-xs text-gray-600 mt-3">
            在根目录 .env 中配置 LLM_API_KEY 等变量后重启后端。
          </p>
        </Card>

        <Card>
          <h3 className="text-sm font-medium text-gray-300 mb-3">邮箱 / 收件箱</h3>
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-300">IMAP 连通性</span>
            <Badge
              tone={
                emailStatus === "ok"
                  ? "success"
                  : emailStatus === "not_configured"
                    ? "warning"
                    : emailStatus === "error"
                      ? "danger"
                      : "default"
              }
            >
              {emailStatus === "ok"
                ? "已连通"
                : emailStatus === "not_configured"
                  ? "未配置"
                  : emailStatus === "error"
                    ? "异常"
                    : "未知"}
            </Badge>
          </div>
          <p className="text-xs text-gray-600 mt-3">
            在根目录 .env 中配置 EMAIL_USER / EMAIL_PASS（Gmail 应用专用密码）后重启后端。
          </p>
        </Card>

        <Card>
          <h3 className="text-sm font-medium text-gray-300 mb-3">MCP 服务器</h3>
          {!mcp?.enabled ? (
            <p className="text-sm text-gray-500">外部 MCP 未启用</p>
          ) : (
            <div className="space-y-2">
              {mcp.servers.map((s) => (
                <div
                  key={s.name}
                  className="flex items-center justify-between text-sm py-1"
                >
                  <span className="text-gray-300">{s.name}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-500">
                      {s.tool_count} 工具
                    </span>
                    <Badge tone={STATUS_TONE[s.status] || "default"}>
                      {STATUS_LABELS[s.status] || s.status}
                    </Badge>
                  </div>
                </div>
              ))}
              <p className="text-xs text-gray-600 mt-2">
                共 {mcp.total_tools} 个外部工具已注册
              </p>
            </div>
          )}
        </Card>

        <Card>
          <h3 className="text-sm font-medium text-gray-300 mb-3">数据主权</h3>
          <p className="text-sm text-gray-500 mb-4">
            导出完整个人数据快照，或从备份文件导入。
          </p>
          <div className="flex flex-wrap gap-3 items-center">
            <Button onClick={handleExport} disabled={exporting}>
              {exporting ? "导出中…" : "导出全部数据"}
            </Button>
            <label className="inline-block">
              <span className="inline-flex px-4 py-2 text-sm rounded-lg font-medium bg-gray-700 hover:bg-gray-600 text-gray-100 cursor-pointer">
                {importing ? "导入中…" : "导入备份（只读）"}
              </span>
              <input
                type="file"
                accept=".json"
                className="hidden"
                onChange={handleImport}
                disabled={importing}
              />
            </label>
          </div>
          <div className="mt-4 flex gap-2 items-center">
            <Input
              value={importConfirm}
              onChange={(e) => setImportConfirm(e.target.value)}
              placeholder="写入导入请输入 DESTROY_AND_IMPORT"
              className="flex-1 text-xs"
            />
            <label className="shrink-0">
              <span
                className={`inline-flex px-3 py-1.5 text-xs rounded-lg font-medium cursor-pointer ${
                  importing || importConfirm !== "DESTROY_AND_IMPORT"
                    ? "bg-gray-800 text-gray-600 cursor-not-allowed"
                    : "bg-red-700 hover:bg-red-600 text-white"
                }`}
              >
                覆盖导入
              </span>
              <input
                type="file"
                accept=".json"
                className="hidden"
                disabled={importing || importConfirm !== "DESTROY_AND_IMPORT"}
                onChange={async (e) => {
                  const file = e.target.files?.[0];
                  if (!file || importConfirm !== "DESTROY_AND_IMPORT") return;
                  setImporting(true);
                  try {
                    const data = JSON.parse(await file.text());
                    await importData(data, false);
                    setImportConfirm("");
                    await load();
                  } catch (err) {
                    addError(
                      err instanceof ApiError ? err.message : "覆盖导入失败",
                      "设置"
                    );
                  } finally {
                    setImporting(false);
                    e.target.value = "";
                  }
                }}
              />
            </label>
          </div>
        </Card>

        <Button variant="ghost" size="sm" onClick={load}>
          刷新状态
        </Button>
      </div>
    </div>
  );
}
