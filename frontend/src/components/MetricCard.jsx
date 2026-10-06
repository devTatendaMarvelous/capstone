export default function MetricCard({ label, value, hint }) {
  return (
    <article className="panel">
      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-moss">{label}</p>
      <p className="mt-3 font-serif text-4xl tracking-tight text-ink">{value ?? "—"}</p>
      {hint ? <div className="mt-3 text-sm text-ink/65">{hint}</div> : null}
    </article>
  );
}
