export function AssumptionBadge({ title }: { title?: string }) {
  return (
    <span className="badge badge-assumption" title={title ?? "Placeholder value: needs your input"}>
      Assumption
    </span>
  );
}

export function UnverifiedBadge({ title }: { title?: string }) {
  return (
    <span className="badge badge-unverified" title={title ?? "Based on unverified rule data"}>
      Unverified data
    </span>
  );
}

export function SafetyBadge({ title }: { title?: string }) {
  return (
    <span className="badge badge-safety" title={title ?? "Could affect product safety: needs human or manufacturer verification"}>
      Safety: verify
    </span>
  );
}

export function ConfidenceBadge({ level }: { level: string }) {
  return <span className={`badge badge-conf-${level}`}>Confidence: {level}</span>;
}
