"use client";

type JobActionResultProps = {
  summary: string;
  result: string;
};

export function JobActionResult({ summary, result }: JobActionResultProps) {
  if (!summary && !result) {
    return null;
  }

  return (
    <div
      className="panel stack"
      style={{ padding: 12, background: "rgba(255,255,255,0.7)" }}
    >
      <div className="eyebrow">Last Action</div>
      {summary ? <div className="muted">{summary}</div> : null}
      {result ? (
        <details>
          <summary style={{ cursor: "pointer" }}>查看原始响应</summary>
          <pre style={{ whiteSpace: "pre-wrap", margin: "12px 0 0 0" }}>{result}</pre>
        </details>
      ) : null}
    </div>
  );
}
