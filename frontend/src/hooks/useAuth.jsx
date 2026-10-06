import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { currentUser, login as loginRequest, logout as clearSession, register as registerRequest, storedUser } from "../services/authService";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => storedUser());
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("smartcrop_access");
    if (!token) {
      setReady(true);
      return;
    }
    currentUser()
      .then(setUser)
      .catch(() => {
        clearSession();
        setUser(null);
      })
      .finally(() => setReady(true));
  }, []);

  const value = useMemo(
    () => ({
      user,
      ready,
      async login(username, password) {
        const next = await loginRequest(username, password);
        setUser(next);
        return next;
      },
      async register(payload) {
        return registerRequest(payload);
      },
      logout() {
        clearSession();
        setUser(null);
      },
    }),
    [user, ready],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}
