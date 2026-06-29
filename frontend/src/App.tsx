import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

type RepoName = "nbn-daemon" | "unity";
type DeployStatus = "idle" | "queued" | "running" | "success" | "failed";

type CredentialStatus = {
  token_valid: boolean;
  token_expires_at: string | null;
  credentials_required: boolean;
};

type DeploymentResponse = {
  deployment_id: string;
  repo: RepoName;
  branch: string;
  filer_ip: string;
  status: "queued" | "running" | "success" | "failed";
  current_phase: string | null;
  progress_percent: number;
  eta_seconds: number | null;
  eta_confidence: "low" | "medium" | "high";
  exit_code: number | null;
  started_at: string;
  completed_at: string | null;
};

type LogPayload = {
  message: string;
  done: boolean;
};

const API_BASE = "/api";

export function App() {
  const params = new URLSearchParams(window.location.search);

  const [repo, setRepo] = useState<RepoName>((params.get("repo") as RepoName) || "nbn-daemon");
  const [branch, setBranch] = useState(params.get("branch") || "main");
  const [filerIp, setFilerIp] = useState(params.get("filerIP") || "10.0.0.100");
  const [branches, setBranches] = useState<string[]>([]);

  const [accessKeyId, setAccessKeyId] = useState("");
  const [secretAccessKey, setSecretAccessKey] = useState("");
  const [sessionToken, setSessionToken] = useState("");

  const [credentialStatus, setCredentialStatus] = useState<CredentialStatus | null>(null);
  const [deploymentId, setDeploymentId] = useState("");
  const [status, setStatus] = useState<DeployStatus>("idle");
  const [message, setMessage] = useState("Ready");
  const [progress, setProgress] = useState(0);
  const [etaSeconds, setEtaSeconds] = useState<number | null>(null);
  const [etaConfidence, setEtaConfidence] = useState<"low" | "medium" | "high">("low");
  const [currentPhase, setCurrentPhase] = useState<string>("queued");
  const [logs, setLogs] = useState<string[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const logsEndRef = useRef<HTMLDivElement | null>(null);

  const credentialsProvided = useMemo(
    () => Boolean(accessKeyId.trim() && secretAccessKey.trim() && sessionToken.trim()),
    [accessKeyId, secretAccessKey, sessionToken],
  );

  const credentialsRequired = repo === "nbn-daemon" && Boolean(credentialStatus?.credentials_required);

  useEffect(() => {
    const run = async () => {
      const response = await fetch(`${API_BASE}/credentials/status`);
      const data = (await response.json()) as CredentialStatus;
      setCredentialStatus(data);
    };
    void run();
  }, []);

  useEffect(() => {
    const run = async () => {
      const response = await fetch(`${API_BASE}/branches/${repo}`);
      if (!response.ok) {
        setBranches([]);
        return;
      }
      const data = (await response.json()) as { branches: string[] };
      setBranches(data.branches);
      if (!data.branches.includes(branch) && data.branches.length > 0) {
        setBranch(data.branches[0]);
      }
    };
    void run();
  }, [repo]);

  useEffect(() => {
    if (!deploymentId) {
      return;
    }

    const poll = window.setInterval(async () => {
      const response = await fetch(`${API_BASE}/deployments/${deploymentId}`);
      if (!response.ok) {
        return;
      }
      const data = (await response.json()) as DeploymentResponse;
      setStatus(data.status);
      setCurrentPhase(data.current_phase ?? "queued");
      setEtaSeconds(data.eta_seconds);
      setEtaConfidence(data.eta_confidence);
      setProgress((prev) => Math.max(prev, data.progress_percent ?? prev));
      if (data.status === "success") {
        setMessage("Deployment completed successfully");
        setProgress(100);
        setEtaSeconds(0);
      } else if (data.status === "failed") {
        setMessage(`Deployment failed (exit code: ${data.exit_code ?? 1})`);
        setProgress(100);
        setEtaSeconds(0);
      } else {
        const phase = data.current_phase ? data.current_phase.replaceAll("_", " ") : "in progress";
        setMessage(`Deployment ${data.status} (${phase})...`);
      }

      if (data.status === "success" || data.status === "failed") {
        window.clearInterval(poll);
        if (wsRef.current) {
          wsRef.current.close();
          wsRef.current = null;
        }
        const credentialResponse = await fetch(`${API_BASE}/credentials/status`);
        const credentialData = (await credentialResponse.json()) as CredentialStatus;
        setCredentialStatus(credentialData);
      }
    }, 1500);

    return () => window.clearInterval(poll);
  }, [deploymentId]);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [logs]);

  const formatDuration = (seconds: number | null): string => {
    if (seconds === null || Number.isNaN(seconds)) {
      return "Estimating...";
    }
    const clamped = Math.max(0, Math.floor(seconds));
    const mins = Math.floor(clamped / 60);
    const secs = clamped % 60;
    if (mins > 0) {
      return `${mins}m ${secs}s`;
    }
    return `${secs}s`;
  };

  const estimateProgress = (line: string, current: number): number => {
    const text = line.toLowerCase();
    if (text.includes("preparing")) return Math.max(current, 8);
    if (text.includes("running: make deploy-rpm") || text.includes("running: python python/tools/sync-dev.py")) {
      return Math.max(current, 15);
    }
    if (text.includes("building rpm") || text.includes("docker build")) return Math.max(current, 35);
    if (text.includes("created build context") || text.includes("copying path dependency")) return Math.max(current, 45);
    if (text.includes("running docker command") || text.includes("deploying")) return Math.max(current, 62);
    if (text.includes("rsync") || text.includes("ssh")) return Math.max(current, 75);
    if (text.includes("deployment finished with exit code 0")) return 100;
    if (text.includes("deployment finished with exit code")) return Math.max(current, 95);
    return current;
  };

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();

    if (credentialsRequired && !credentialsProvided) {
      setMessage("AWS credentials are required because token is expired or missing.");
      return;
    }

    setStatus("queued");
    setMessage("Starting deployment...");
    setProgress(3);
    setEtaSeconds(null);
    setEtaConfidence("low");
    setCurrentPhase("queued");
    setLogs([]);

    const payload = {
      repo,
      branch,
      filer_ip: filerIp,
      aws: {
        access_key_id: accessKeyId,
        secret_access_key: secretAccessKey,
        session_token: sessionToken,
      },
    };

    const response = await fetch(`${API_BASE}/deploy`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const err = await response.text();
      setStatus("failed");
      setMessage(`Unable to start deployment: ${err}`);
      return;
    }

    const data = (await response.json()) as { deployment_id: string };
    setDeploymentId(data.deployment_id);
    setStatus("running");
    setMessage(`Deployment started (${data.deployment_id.slice(0, 8)}...)`);
    setProgress(8);

    const wsProtocol = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${wsProtocol}://${window.location.host}/api/ws/logs/${data.deployment_id}`);
    wsRef.current = ws;
    ws.onmessage = (event) => {
      let payload: LogPayload | null = null;
      try {
        payload = JSON.parse(event.data) as LogPayload;
      } catch {
        return;
      }

      if (!payload || !payload.message) {
        return;
      }

      setLogs((prev) => {
        const next = [...prev, payload.message];
        if (next.length > 500) {
          return next.slice(next.length - 500);
        }
        return next;
      });

      setProgress((prev) => estimateProgress(payload!.message, prev));
      if (payload.done) {
        setProgress(100);
      }
    };

    ws.onerror = () => {
      setLogs((prev) => [...prev, "[websocket] log stream disconnected"]);
    };
  };

  return (
    <main className="page">
      <section className="card">
        <h1>Deploy Tool</h1>
        <p className="subtitle">Clean deployment flow for nbn-daemon and unity</p>

        <form className="form" onSubmit={onSubmit}>
          <label>
            Repository
            <select value={repo} onChange={(e) => setRepo(e.target.value as RepoName)} disabled={status === "running"}>
              <option value="nbn-daemon">nbn-daemon</option>
              <option value="unity">unity</option>
            </select>
          </label>

          <label>
            Branch
            <input
              list="branch-options"
              value={branch}
              onChange={(e) => setBranch(e.target.value)}
              disabled={status === "running"}
            />
            <datalist id="branch-options">
              {branches.map((item) => (
                <option value={item} key={item} />
              ))}
            </datalist>
          </label>

          <label>
            Filer IP
            <input value={filerIp} onChange={(e) => setFilerIp(e.target.value)} disabled={status === "running"} />
          </label>

          <div className="aws-block">
            <div className="aws-title">AWS Credentials</div>
            <div className="aws-note">
              {credentialsRequired
                ? "Mandatory now: token is expired or missing."
                : "Optional now: fill to refresh token proactively."}
            </div>

            <label>
              Access Key ID
              <input value={accessKeyId} onChange={(e) => setAccessKeyId(e.target.value)} disabled={status === "running"} />
            </label>

            <label>
              Secret Access Key
              <input
                type="password"
                value={secretAccessKey}
                onChange={(e) => setSecretAccessKey(e.target.value)}
                disabled={status === "running"}
              />
            </label>

            <label>
              Session Token
              <input
                type="password"
                value={sessionToken}
                onChange={(e) => setSessionToken(e.target.value)}
                disabled={status === "running"}
              />
            </label>
          </div>

          <button type="submit" disabled={status === "running"}>
            {status === "running" ? "Deploying..." : "Deploy"}
          </button>
        </form>

        <div className={`status ${status}`}>
          <strong>Status:</strong> {status}
          <div>{message}</div>
          <div className="progress-wrap" aria-label="Deployment progress">
            <div className="progress-track">
              <div className="progress-fill" style={{ width: `${progress}%` }} />
            </div>
            <div className="progress-label">{progress}%</div>
            <div className="progress-meta">
              ETA: {formatDuration(etaSeconds)} | confidence: {etaConfidence} | phase: {currentPhase.replaceAll("_", " ")}
            </div>
          </div>
          {credentialStatus?.token_expires_at ? <div>Token expires at: {credentialStatus.token_expires_at}</div> : null}
          {deploymentId ? <div>Deployment ID: {deploymentId}</div> : null}
        </div>

        <section className="logs-panel" aria-live="polite">
          <h2>Real-time Logs</h2>
          <div className="logs-body">
            {logs.length === 0 ? <div className="logs-empty">Logs will appear after deployment starts.</div> : null}
            {logs.map((line, index) => (
              <div key={`${index}-${line.slice(0, 16)}`} className="log-line">
                {line}
              </div>
            ))}
            <div ref={logsEndRef} />
          </div>
        </section>
      </section>
    </main>
  );
}
