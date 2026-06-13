import { useCallback, type TextareaHTMLAttributes } from "react";

interface Props extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  autoGrow?: boolean;
}

export function Textarea({ autoGrow = false, className = "", onInput, ...props }: Props) {
  const handleInput = useCallback(
    (e: React.FormEvent<HTMLTextAreaElement>) => {
      if (autoGrow) {
        const el = e.currentTarget;
        el.style.height = "auto";
        el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
      }
      if (onInput) {
        onInput(e as unknown as React.InputEvent<HTMLTextAreaElement>);
      }
    },
    [autoGrow, onInput]
  );

  return (
    <textarea
      className={`bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm outline-none focus:border-emerald-600 text-gray-100 placeholder-gray-500 ${className}`}
      onInput={handleInput}
      {...props}
    />
  );
}

export function Input({
  className = "",
  ...props
}: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={`bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm outline-none focus:border-emerald-600 text-gray-100 placeholder-gray-500 ${className}`}
      {...props}
    />
  );
}
