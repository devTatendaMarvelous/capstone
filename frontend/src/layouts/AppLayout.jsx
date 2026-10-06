import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

const LINKS = [
  ["/", "Dashboard"],
  ["/predict", "Predict"],
  ["/history", "History"],
  ["/analytics", "Analytics"],
  ["/reports", "Reports"],
  ["/datasets", "Datasets"],
  ["/models", "Models"],
  ["/profile", "Profile"],
];

export default function AppLayout() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const links = user?.role === "admin" ? [...LINKS, ["/admin", "Admin"]] : LINKS;

  return (
    <div className="min-h-screen bg-canvas text-ink lg:grid lg:grid-cols-[248px_1fr]">
      <aside className={`${open ? "translate-x-0" : "-translate-x-full"} fixed inset-y-0 z-30 flex w-[248px] flex-col bg-[#10281c] text-white transition lg:static lg:translate-x-0`}>
        <div className="flex items-center gap-3 px-5 py-6">
          <span className="grid h-10 w-10 place-items-center rounded-2xl bg-lime font-serif text-lg text-ink">S</span>
          <div>
            <p className="font-serif text-xl leading-none">SmartCrop</p>
            <p className="mt-1 text-xs text-white/60">Macheke maize</p>
          </div>
        </div>
        <nav className="flex flex-1 flex-col gap-1 px-3">
          {links.map(([to, label]) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                `rounded-xl px-3 py-2 text-sm font-medium transition ${isActive ? "bg-white/15 text-white" : "text-white/70 hover:bg-white/10 hover:text-white"}`
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="m-3 rounded-2xl bg-white/10 p-3">
          <p className="text-sm font-semibold">{user?.username}</p>
          <p className="text-xs capitalize text-white/60">{user?.role}</p>
          <button type="button" onClick={logout} className="mt-3 w-full rounded-xl bg-white px-3 py-2 text-sm font-semibold text-ink">
            Sign out
          </button>
        </div>
      </aside>
      {open ? <button type="button" aria-label="Close menu" className="fixed inset-0 z-20 bg-ink/40 lg:hidden" onClick={() => setOpen(false)} /> : null}
      <div className="min-w-0">
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-line/80 bg-canvas/90 px-4 py-3 backdrop-blur lg:hidden">
          <p className="font-serif text-lg">SmartCrop</p>
          <button type="button" className="btn-secondary px-3 py-1.5" onClick={() => setOpen(true)}>
            Menu
          </button>
        </div>
        <main className="mx-auto max-w-6xl px-4 py-6 lg:px-8 lg:py-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
