"use client";

import { useState, useEffect } from "react";

export function useAuth() {
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const t = localStorage.getItem("access_token");
    setToken(t);
    setLoading(false);
  }, []);

  const logout = () => {
    localStorage.removeItem("access_token");
    setToken(null);
    window.location.href = "/auth/login";
  };

  return { token, loading, logout, isAuthenticated: !!token };
}
