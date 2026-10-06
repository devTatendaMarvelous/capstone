import { useState } from "react";
import ErrorState from "../components/ErrorState";
import { useAuth } from "../hooks/useAuth";
import api, { errorMessage } from "../services/api";

export default function ProfilePage() {
  const { user } = useAuth();
  const [message, setMessage] = useState("");
  const [saved, setSaved] = useState("");

  async function onSubmit(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      await api.patch("/api/v1/auth/me/", {
        first_name: form.get("first_name"),
        last_name: form.get("last_name"),
        email: form.get("email"),
      });
      setSaved("Profile saved.");
      setMessage("");
    } catch (error) {
      setMessage(errorMessage(error));
    }
  }

  return (
    <section className="panel max-w-lg">
      <p className="page-kicker">Account</p>
      <h1 className="page-title">Profile</h1>
      <p className="mt-2 text-sm">Role: {user?.role}. Roles are assigned by an administrator.</p>
      <ErrorState message={message} />
      {saved ? <p className="mt-2 text-sm text-leaf">{saved}</p> : null}
      <form onSubmit={onSubmit} className="mt-4 space-y-3">
        <label className="block text-sm">
          Email
          <input name="email" type="email" defaultValue={user?.email || ""} className="input" />
        </label>
        <label className="block text-sm">
          First name
          <input name="first_name" defaultValue={user?.first_name || ""} className="input" />
        </label>
        <label className="block text-sm">
          Last name
          <input name="last_name" defaultValue={user?.last_name || ""} className="input" />
        </label>
        <button type="submit" className="btn-primary">
          Save
        </button>
      </form>
    </section>
  );
}
