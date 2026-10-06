export default function EmptyState({ title, body }) {
  return (
    <div className="rounded-2xl border border-dashed border-line bg-canvas px-4 py-10 text-center">
      <p className="font-serif text-lg text-ink">{title}</p>
      <p className="mx-auto mt-2 max-w-sm text-sm text-ink/60">{body}</p>
    </div>
  );
}
