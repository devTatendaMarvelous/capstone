export default function ReportButton({ label, onClick, busy }) {
  return (
    <button type="button" onClick={onClick} disabled={busy} className="btn-secondary">
      {busy ? "Preparing…" : label}
    </button>
  );
}
