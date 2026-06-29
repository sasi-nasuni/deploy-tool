import json
from datetime import datetime, timezone
from pathlib import Path


class EtaManager:
    HISTORY_FILE = Path("~/.deploy_tool/deploy_eta_history.json").expanduser()
    MAX_SAMPLES = 30

    def __init__(self) -> None:
        self.HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        self._history = self._load_history()

    def _load_history(self) -> dict[str, dict[str, list[float]]]:
        if not self.HISTORY_FILE.exists():
            return {}
        try:
            data = json.loads(self.HISTORY_FILE.read_text())
            if not isinstance(data, dict):
                return {}
            return data
        except Exception:
            return {}

    def _save_history(self) -> None:
        self.HISTORY_FILE.write_text(json.dumps(self._history, indent=2))

    def _bucket(self, repo: str) -> dict[str, list[float]]:
        bucket = self._history.setdefault(repo, {})
        for key in ("total", "git_prep", "deploy_exec", "finalize"):
            bucket.setdefault(key, [])
        return bucket

    def _rolling_avg(self, values: list[float]) -> float | None:
        if not values:
            return None
        return sum(values) / len(values)

    def estimate(self, state: dict) -> tuple[int | None, str]:
        repo = state.get("repo", "")
        status = state.get("status")
        if status in {"success", "failed"}:
            return 0, "high"

        started_at = state.get("started_at")
        if not isinstance(started_at, datetime):
            return None, "low"

        now = datetime.now(timezone.utc)
        elapsed = max(0.0, (now - started_at).total_seconds())

        bucket = self._bucket(repo)
        total_avg = self._rolling_avg(bucket.get("total", []))
        if total_avg is None:
            phase_targets = {
                "queued": 90.0,
                "git_prep": 120.0,
                "deploy_exec": 660.0,
                "finalize": 45.0,
            }
            current_phase = state.get("current_phase") or "queued"
            base_total = phase_targets.get(current_phase, 900.0)
            remaining = int(max(0.0, base_total - elapsed))
            return remaining, "low"

        remaining = int(max(0.0, total_avg - elapsed))
        sample_count = len(bucket.get("total", []))
        if sample_count >= 12:
            confidence = "high"
        elif sample_count >= 5:
            confidence = "medium"
        else:
            confidence = "low"
        return remaining, confidence

    def record_run(self, repo: str, phase_durations: dict[str, float], total_seconds: float) -> None:
        bucket = self._bucket(repo)

        def push(key: str, value: float) -> None:
            bucket[key].append(float(value))
            if len(bucket[key]) > self.MAX_SAMPLES:
                bucket[key] = bucket[key][-self.MAX_SAMPLES :]

        push("total", total_seconds)
        for phase in ("git_prep", "deploy_exec", "finalize"):
            if phase in phase_durations:
                push(phase, phase_durations[phase])
        self._save_history()
