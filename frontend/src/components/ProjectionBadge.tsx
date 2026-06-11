import type { KeyInsightsParsed } from "../api/client";

interface Props {
  parsed?: KeyInsightsParsed;
  className?: string;
}

/** Identity RFC N5 — marks narrative as system projection, not ratified identity. */
export default function ProjectionBadge({ parsed, className = "" }: Props) {
  if (!parsed?.projection) {
    return null;
  }
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-medium bg-amber-950/60 text-amber-300 border border-amber-800/50 ${className}`}
      title="Identity Projection：系统编织的叙事草稿，不代表对你身份的认定"
    >
      系统投影
      {parsed.not_ratified ? " · 未署名" : ""}
    </span>
  );
}
