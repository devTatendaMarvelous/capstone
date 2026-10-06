import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import ErrorState from "../components/ErrorState";
import { useAuth } from "../hooks/useAuth";
import { errorMessage } from "../services/api";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [message, setMessage] = useState("");

  async function onSubmit(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      await login(form.get("username"), form.get("password"));
      navigate("/");
    } catch (error) {
      setMessage(errorMessage(error));
    }
  }

  return (
    <main className="grid min-h-screen lg:grid-cols-2">
      <section className="hidden flex-col justify-between bg-[#10281c] p-10 text-white lg:flex">
        <div className="flex items-center gap-3">
          <span className="grid h-11 w-11 place-items-center rounded-2xl bg-lime font-serif text-xl text-ink">S</span>
          <p className="font-serif text-2xl">SmartCrop</p>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-lime">Macheke · Mashonaland East</p>
          <h1 className="mt-3 max-w-md font-serif text-5xl leading-tight">Maize yield, estimated before harvest.</h1>
          <p className="mt-4 max-w-sm text-white/70">
            A result is a model estimate in tonnes per hectare, not a guaranteed harvest.
          </p>
        </div>
        <p className="text-sm text-white/50">Trained on labelled synthetic development data.</p>
      </section>
      <section className="flex items-center justify-center px-4 py-16">
        <div className="w-full max-w-md">
          <p className="font-serif text-4xl text-ink lg:hidden">SmartCrop</p>
          <h2 className="font-serif text-3xl text-ink">Sign in</h2>
          <p className="mt-2 text-sm text-ink/65">Use a demo account or a farmer account you registered.</p>
          <form onSubmit={onSubmit} className="panel mt-6 space-y-4">
            <ErrorState message={message} />
            <label className="block text-sm font-medium">
              Username
              <input name="username" required className="input" />
            </label>
            <label className="block text-sm font-medium">
              Password
              <input name="password" type="password" required className="input" />
            </label>
            <button type="submit" className="btn-primary w-full">
              Sign in
            </button>
          </form>
          <p className="mt-4 text-sm">
            Need a farmer account? <Link to="/register" className="font-semibold text-leaf">Register</Link>
          </p>
          <p className="mt-3 rounded-2xl bg-mist px-4 py-3 text-sm text-ink/80">
            Demo sign-in: username <span className="font-semibold">admin</span>, password <span className="font-semibold">password</span>. The same password works for researcher, analyst, and farmer.
          </p>
        </div>
      </section>
    </main>
  );
}
