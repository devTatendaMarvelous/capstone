export default function ModelBadge({ model }) {
  if (!model) return <span className="text-sm text-ink/60">No active model</span>;
  return (
    <span className="inline-flex items-center gap-2 rounded-full bg-mist px-3 py-1 text-sm text-leaf">
      <span className="h-1.5 w-1.5 rounded-full bg-leaf" />
      <span className="font-semibold">{model.algorithm || model.name}</span>
      <span className="text-leaf/70">v{model.version}</span>
    </span>
  );
}
