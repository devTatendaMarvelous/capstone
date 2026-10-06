import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import ErrorState from "../components/ErrorState";
import { useAuth } from "../hooks/useAuth";
import { errorMessage } from "../services/api";

const FIELDS = [
  ["username", "Username", true],
  ["email", "Email", true],
  ["first_name", "First name", false],
  ["last_name", "Last name", false],
];

export default function RegisterPage() {
  const { register, login } = useAuth();
  const navigate = useNavigate();
  const [message, setMessage] = useState("");

  async function onSubmit(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const payload = {
      username: form.get("username"),
      email: form.get("email"),
      password: form.get("password"),
      first_name: form.get("first_name"),
      last_name: form.get("last_name"),
    };
    try {
      await register(payload);
      await login(payload.username, payload.password);
      navigate("/");
    } catch (error) {
      setMessage(errorMessage(error));
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-canvas px-4 py-16">
      <div className="w-full max-w-md">
        <p className="page-kicker">Farmer account</p>
        <h1 className="page-title">Create your account</h1>
        <p className="mt-2 text-sm text-ink/65">Registration creates a farmer account. An administrator assigns other roles.</p>
        <form onSubmit={onSubmit} className="panel mt-6 space-y-4">
          <ErrorState message={message} />
          {FIELDS.map(([name, label, required]) => (
            <label key={name} className="block text-sm font-medium">
              {label}
              <input name={name} type={name === "email" ? "email" : "text"} required={required} className="input" />
            </label>
          ))}
          <label className="block text-sm font-medium">
            Password
            <input name="password" type="password" minLength={8} required className="input" />
          </label>
          <button type="submit" className="btn-primary w-full">
            Register
          </button>
        </form>
        <p className="mt-4 text-sm">
          Already registered? <Link to="/login" className="font-semibold text-leaf">Sign in</Link>
        </p>
      </div>
    </main>
  );
}
