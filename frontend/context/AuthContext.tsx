"use client";

import { createContext, useContext, useState, useEffect, ReactNode } from "react";

interface AuthContextType {
  token: string | null;
  isAuthenticated: boolean;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType>({
  token: null,
  isAuthenticated: false,
  logout: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    setToken(localStorage.getItem("access_token"));
  }, []);

  const logout = () => {
    localStorage.removeItem("access_token");
    setToken(null);
    window.location.href = "/auth/login";
  };

  return (
    <AuthContext.Provider value={{ token, isAuthenticated: !!token, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export { AuthContext };
