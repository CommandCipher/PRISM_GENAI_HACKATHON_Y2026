import { useEffect, useMemo, useState } from "react";
import {
  ArrowUpRight,
  CheckCircle2,
  ChevronDown,
  Clipboard,
  Cpu,
  ExternalLink,
  Loader2,
  MessageSquare,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  Zap
} from "lucide-react";

const EXAMPLE_QUERIES = [
  "My touchscreen is not responding",
  "My screen is completely blank",
  "My phone is behaving weirdly"
];

async function troubleshoot(query) {
  const response = await fetch("/api/v1/troubleshoot", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query })
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data?.detail?.[0]?.msg || "The troubleshooting request failed.");
  }
  return data;
}

async function getHealth() {
  const response = await fetch("/health");
  if (!response.ok) throw new Error("Backend unavailable");
  return response.json();
}

function Badge({ children, tone = "neutral" }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

function Deeplink({ href }) {
  const [copied, setCopied] = useState(false);

  if (!href) return null;

  async function copy() {
    try {
      await navigator.clipboard.writeText(href);
      setCopied(true);
      setTimeout(() => setCopied(false), 1400);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="deeplink-row">
      <button className="settings-button" onClick={() => { window.location.href = href; }}>
        <ExternalLink size={15} />
        Open Settings
      </button>
      <button className="copy-button" onClick={copy} title="Copy deeplink">
        <Clipboard size={15} />
        {copied ? "Copied" : "Copy link"}
      </button>
    </div>
  );
}

function StepGroup({ group, index }) {
  return (
    <div className="step-group">
      {group.steps?.map((step, stepIndex) => (
        <div className="step" key={`${index}-${stepIndex}`}>
          <div className="step-number">{stepIndex + 1}</div>
          <div className="step-text">{step}</div>
        </div>
      ))}
      {group.actionableDeeplink?.deeplink && (
        <Deeplink href={group.actionableDeeplink.deeplink} />
      )}
      {group.validationDeeplink?.deeplink && (
        <div className="validation">
          <ShieldCheck size={14} />
          Verify: {group.validationDeeplink.key}
        </div>
      )}
    </div>
  );
}

function ActionCard({ action, index }) {
  const [open, setOpen] = useState(index < 2);
  const tone =
    action.category === "critical"
      ? "critical"
      : action.category === "manual"
        ? "manual"
        : "auto";

  return (
    <article className={`action-card ${tone}`}>
      <button className="action-header" onClick={() => setOpen(!open)}>
        <div className="action-index">{String(index + 1).padStart(2, "0")}</div>
        <div className="action-heading">
          <div className="action-title-row">
            <h3>{action.actionName}</h3>
            <Badge tone={tone}>{action.category || "manual"}</Badge>
          </div>
          <p>{action.description}</p>
        </div>
        <ChevronDown className={`chevron ${open ? "open" : ""}`} size={19} />
      </button>

      {open && (
        <div className="action-body">
          {action.stepGroups?.map((group, i) => (
            <StepGroup group={group} index={i} key={i} />
          ))}
        </div>
      )}
    </article>
  );
}

function ResultView({ result }) {
  const context = result?.response?.contexts?.[0];
  const metadata = result?.metadata;

  if (!context) {
    return (
      <div className="empty-result">
        <div className="empty-icon"><MessageSquare size={22} /></div>
        <h2>No validated troubleshooting path</h2>
        <p>
          The engine could not find a validated scenario for this complaint.
          No unsupported troubleshooting steps were generated.
        </p>
      </div>
    );
  }

  return (
    <section className="results">
      <div className="result-summary">
        <div>
          <div className="eyebrow">Validated troubleshooting scenario</div>
          <h2>{context.title}</h2>
          <p>{context.goal}</p>
        </div>
        <div className="score-card">
          <span>Confidence</span>
          <strong>{Math.round((context.score || 0) * 100)}%</strong>
        </div>
      </div>

      {metadata && (
        <div className="telemetry">
          {metadata.fast_path && (
            <Badge tone="fast"><Zap size={13} /> Fast Path</Badge>
          )}
          {metadata.llm_call_avoided && (
            <Badge tone="fast"><CheckCircle2 size={13} /> LLM Call Avoided</Badge>
          )}
          <span>Scenario: <b>{metadata.scenario_id || "—"}</b></span>
          <span>Latency: <b>{metadata.latency_ms ?? "—"} ms</b></span>
        </div>
      )}

      <div className="actions">
        {context.actions?.map((action, i) => (
          <ActionCard action={action} index={i} key={i} />
        ))}
      </div>
    </section>
  );
}

export default function App() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [health, setHealth] = useState(null);

  useEffect(() => {
    getHealth().then(setHealth).catch(() => setHealth(null));
  }, []);

  const status = useMemo(() => {
    if (!health) return "Checking backend";
    return health.status === "ok" ? "Backend connected" : "Backend unavailable";
  }, [health]);

  async function runTroubleshoot(value = query) {
    const trimmed = value.trim();
    if (trimmed.length < 3 || loading) return;

    setQuery(trimmed);
    setLoading(true);
    setError("");

    try {
      const data = await troubleshoot(trimmed);
      setResult(data);
    } catch (err) {
      setError(err.message);
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  function reset() {
    setQuery("");
    setResult(null);
    setError("");
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark"><Sparkles size={19} /></div>
          <div>
            <strong>Smart Troubleshooter</strong>
            <span>Samsung PRISM • Theme 2</span>
          </div>
        </div>
        <div className="system-status">
          <span className={`status-dot ${health ? "online" : ""}`} />
          {status}
          {health && (
            <span className="catalog-count">
              {health.scenarios_loaded} scenarios · {health.deeplinks_loaded} deeplinks
            </span>
          )}
        </div>
      </header>

      <main>
        <section className="hero">
          <div className="hero-copy">
            <div className="hero-kicker"><Cpu size={15} /> AI-guided device support</div>
            <h1>What’s wrong with<br /><span>your device?</span></h1>
            <p>
              Describe the problem naturally. The engine finds a validated
              troubleshooting path and guides you through it step by step.
            </p>
          </div>

          <div className="query-card">
            <div className="query-label">Describe your issue</div>
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if ((e.ctrlKey || e.metaKey) && e.key === "Enter") runTroubleshoot();
              }}
              placeholder="e.g. My touchscreen is not responding"
              rows={3}
            />
            <div className="query-footer">
              <div className="examples">
                {EXAMPLE_QUERIES.map((example) => (
                  <button key={example} onClick={() => setQuery(example)}>
                    {example}
                  </button>
                ))}
              </div>
              <button
                className="troubleshoot-button"
                onClick={() => runTroubleshoot()}
                disabled={loading || query.trim().length < 3}
              >
                {loading ? <Loader2 className="spin" size={17} /> : <ArrowUpRight size={17} />}
                {loading ? "Analyzing..." : "Troubleshoot"}
              </button>
            </div>
          </div>
        </section>

        {error && (
          <div className="error-banner">
            <strong>Request failed</strong>
            <span>{error}</span>
            <button onClick={() => runTroubleshoot()}>Retry</button>
          </div>
        )}

        {result ? (
          <>
            <div className="section-heading">
              <div>
                <div className="eyebrow">Engine response</div>
                <h2>Troubleshooting plan</h2>
              </div>
              <button className="reset-button" onClick={reset}>
                <RotateCcw size={15} /> New issue
              </button>
            </div>
            <ResultView result={result} />
          </>
        ) : (
          <section className="how-it-works">
            <div className="section-heading">
              <div>
                <div className="eyebrow">How it works</div>
                <h2>From vague complaint to validated action</h2>
              </div>
            </div>
            <div className="flow-grid">
              {[
                ["01", "Understand", "Natural-language query enrichment and semantic retrieval."],
                ["02", "Structure", "Device Brain converts the selected scenario into ordered actions and steps."],
                ["03", "Validate", "Catalog-grounded deeplinks pass through the validation guard."],
                ["04", "Accelerate", "Validated scenarios can use the LLM-free semantic fast path."]
              ].map(([num, title, text]) => (
                <div className="flow-card" key={num}>
                  <span>{num}</span>
                  <h3>{title}</h3>
                  <p>{text}</p>
                </div>
              ))}
            </div>
          </section>
        )}
      </main>

      <footer>
        <span>CommandCipher</span>
        <span>Language Brain + Device Brain</span>
        <span>FastAPI · React · FAISS · Pydantic</span>
      </footer>
    </div>
  );
}