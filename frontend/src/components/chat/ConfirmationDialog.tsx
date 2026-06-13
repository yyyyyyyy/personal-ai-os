import { toolLabel, describeToolAction } from "../../utils/toolLabels";
import Button from "../ui/Button";

interface ToolCall {
  index: number;
  id: string;
  function_name: string;
  arguments: string;
}

interface Props {
  toolCall: ToolCall;
  onConfirm: () => void;
  onDeny: () => void;
}

const PREVIEW_LIMIT = 400;

function parseArgs(args: string): Record<string, unknown> {
  try {
    return JSON.parse(args);
  } catch {
    return {};
  }
}

function truncate(text: string, max = PREVIEW_LIMIT): string {
  if (text.length <= max) return text;
  return `${text.slice(0, max)}…`;
}

function ExpandableText({
  text,
  className,
}: {
  text: string;
  className: string;
}) {
  const preview = truncate(text);
  const isTruncated = text.length > PREVIEW_LIMIT;

  return (
    <div className={className}>
      <div className="whitespace-pre-wrap break-all">{preview}</div>
      {isTruncated && (
        <details className="mt-1">
          <summary className="cursor-pointer text-gray-500 hover:text-gray-400">
            查看完整内容
          </summary>
          <pre className="mt-1 max-h-40 overflow-y-auto whitespace-pre-wrap break-all text-gray-400">
            {text}
          </pre>
        </details>
      )}
    </div>
  );
}

function PatchPreview({ args }: { args: Record<string, unknown> }) {
  const oldString = typeof args.old_string === "string" ? args.old_string : "";
  const newString = typeof args.new_string === "string" ? args.new_string : "";
  if (!oldString && !newString) return null;

  return (
    <div className="mb-3 rounded border border-amber-700/40 bg-gray-950/80 p-2 text-xs font-mono">
      <div className="mb-1 text-amber-400/70">变更预览</div>
      {oldString && (
        <ExpandableText
          text={`− ${oldString}`}
          className="text-red-300/90"
        />
      )}
      {newString && (
        <ExpandableText
          text={`+ ${newString}`}
          className="text-green-300/90"
        />
      )}
      {args.replace_all === true && (
        <div className="mt-1 text-gray-500">replace_all = true</div>
      )}
    </div>
  );
}

function WriteFilePreview({ args }: { args: Record<string, unknown> }) {
  const content = typeof args.content === "string" ? args.content : "";
  if (!content) return null;

  return (
    <div className="mb-3 rounded border border-amber-700/40 bg-gray-950/80 p-2 text-xs font-mono">
      <div className="mb-1 text-amber-400/70">写入内容预览</div>
      <ExpandableText text={content} className="text-amber-200/90" />
    </div>
  );
}

export default function ConfirmationDialog({ toolCall, onConfirm, onDeny }: Props) {
  const label = toolLabel(toolCall.function_name);
  const args = parseArgs(toolCall.arguments);
  const description = describeToolAction(toolCall.function_name, args);
  const isPatch = toolCall.function_name === "apply_patch";
  const isWrite = toolCall.function_name === "write_file";

  return (
    <div className="bg-amber-900/30 border border-amber-600/50 rounded-lg p-4">
      <div className="flex items-start gap-3">
        <div className="text-amber-400 text-xl mt-0.5 shrink-0">⚠️</div>
        <div className="flex-1 min-w-0">
          <h4 className="text-amber-300 font-medium mb-1">
            确认{label}
          </h4>
          {description && (
            <p className="text-amber-400/60 text-sm mb-3 whitespace-pre-wrap">
              {description}
            </p>
          )}
          {isPatch && <PatchPreview args={args} />}
          {isWrite && <WriteFilePreview args={args} />}
          <details className="mb-3">
            <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-400">
              查看详细参数
            </summary>
            <pre className="bg-gray-950 p-2 mt-1 rounded text-xs text-gray-400 overflow-x-auto max-h-24 overflow-y-auto">
              {JSON.stringify(args, null, 2)}
            </pre>
          </details>
          <div className="flex gap-2">
            <Button size="sm" onClick={onConfirm}>
              确认执行
            </Button>
            <Button size="sm" variant="secondary" onClick={onDeny}>
              取消
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
