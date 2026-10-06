export default function ErrorState({ message }) {
  if (!message) return null;
  return (
    <p role="alert" className="rounded-xl bg-red-50 px-4 py-3 text-sm text-clay ring-1 ring-clay/20">
      {message}
    </p>
  );
}
