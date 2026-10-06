export default function LoadingState({ label = "Loading SmartCrop…" }) {
  return (
    <div className="panel flex items-center gap-3 text-sm text-moss">
      <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-leaf" />
      {label}
    </div>
  );
}
