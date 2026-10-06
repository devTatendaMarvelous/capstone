export default function DatasetStatus({ status }) {
  const tone = status === "validated" ? "bg-mist text-leaf" : status === "failed" ? "bg-red-100 text-clay" : "bg-amber-50 text-clay";
  return <span className={`rounded-full px-2 py-1 text-xs font-semibold uppercase ${tone}`}>{status}</span>;
}
