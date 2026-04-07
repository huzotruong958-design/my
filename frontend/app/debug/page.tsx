import { AgentProbeForm } from "@/components/agent-probe-form";

export default function DebugPage() {
  return (
    <div className="stack">
      <div className="hero">
        <div className="eyebrow">Debug</div>
        <h1 style={{ margin: 0 }}>单 Agent 联调</h1>
        <p className="muted">当某个真实模型调用不稳定时，先在这里单测，不要每次都跑完整条公众号生成链路。</p>
      </div>
      <AgentProbeForm />
    </div>
  );
}
