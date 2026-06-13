import { useState } from "react";
import {
  getSystemHealth,
  getLlmProviders,
  ApiError,
} from "../../api/client";
import Button from "../ui/Button";
import Card from "../ui/Card";

const STEPS = [
  { title: "检查后端", description: "确认 Personal AI Runtime 后端已启动" },
  { title: "LLM 配置", description: "验证 LLM API 提供商可用" },
  { title: "核心功能", description: "了解对话、目标、收件箱与数据导出" },
];

interface Props {
  onComplete: () => void;
}

export default function OnboardingWizard({ onComplete }: Props) {
  const [step, setStep] = useState(0);
  const [checking, setChecking] = useState(false);
  const [message, setMessage] = useState("");
  const [messageOk, setMessageOk] = useState(true);

  const checkHealth = async (): Promise<boolean> => {
    setChecking(true);
    try {
      const health = await getSystemHealth();
      setMessage(`后端运行正常 (v${health.version})`);
      setMessageOk(true);
      return true;
    } catch (err) {
      setMessage(
        err instanceof ApiError ? err.message : "无法连接后端，请先启动服务"
      );
      setMessageOk(false);
      return false;
    } finally {
      setChecking(false);
    }
  };

  const checkLlm = async (): Promise<boolean> => {
    setChecking(true);
    try {
      const res = await getLlmProviders();
      const count = res.providers?.length ?? 0;
      if (count === 0) {
        setMessage("未检测到 LLM 提供商，请在 .env 配置 LLM_API_KEY");
        setMessageOk(false);
        return false;
      }
      setMessage(`已配置 ${count} 个提供商，默认：${res.default}`);
      setMessageOk(true);
      return true;
    } catch (err) {
      setMessage(err instanceof ApiError ? err.message : "检查 LLM 失败");
      setMessageOk(false);
      return false;
    } finally {
      setChecking(false);
    }
  };

  const handleNext = async () => {
    if (step === 0) {
      const ok = await checkHealth();
      if (!ok) return;
      setStep(1);
      setMessage("");
      return;
    }
    if (step === 1) {
      const ok = await checkLlm();
      if (!ok) return;
      setStep(2);
      setMessage("");
      return;
    }
    localStorage.setItem("onboarding_done", "1");
    onComplete();
  };

  const current = STEPS[step];

  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/70">
      <Card className="max-w-md w-full mx-4">
        <div className="text-xs text-emerald-500 mb-2">
          首次引导 {step + 1}/{STEPS.length}
        </div>
        <h2 className="text-xl font-semibold text-gray-100">{current.title}</h2>
        <p className="text-sm text-gray-400 mt-2">{current.description}</p>

        {step < 2 && (
          <div className="mt-4">
            <Button
              size="sm"
              variant="secondary"
              onClick={step === 0 ? checkHealth : checkLlm}
              disabled={checking}
            >
              {checking ? "检查中…" : "运行检查"}
            </Button>
            {message && (
              <p
                className={`text-xs mt-2 ${messageOk ? "text-emerald-400" : "text-red-400"}`}
              >
                {message}
              </p>
            )}
          </div>
        )}

        {step === 2 && (
          <ul className="mt-4 text-sm text-gray-400 space-y-2 list-disc pl-5">
            <li>对话：与 AI 交流，支持工具调用与审批</li>
            <li>目标：追踪进度，停滞自动提醒</li>
            <li>收件箱：邮件分类与 AI 处理</li>
            <li>设置：一键导出/导入个人数据</li>
          </ul>
        )}

        <div className="flex justify-between mt-6">
          <Button
            size="sm"
            variant="ghost"
            onClick={() => {
              localStorage.setItem("onboarding_done", "1");
              onComplete();
            }}
          >
            跳过
          </Button>
          <Button size="sm" onClick={handleNext} disabled={checking}>
            {step === STEPS.length - 1 ? "开始使用" : "下一步"}
          </Button>
        </div>
      </Card>
    </div>
  );
}
