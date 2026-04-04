"use client";

import { useEffect, useState } from "react";

import { getCurrentUser, loginAdmin } from "@/shared/api/client";
import type { TokenPair, User } from "@/shared/api/types";

const STORAGE_KEY = "portfolio-admin-tokens";

export function useAdminAuth() {
  const [tokens, setTokens] = useState<TokenPair | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    const restoreSession = async () => {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) {
        setIsReady(true);
        return;
      }

      try {
        const parsed = JSON.parse(raw) as TokenPair;
        const me = await getCurrentUser(parsed.access_token);
        setTokens(parsed);
        setUser(me);
      } catch {
        window.localStorage.removeItem(STORAGE_KEY);
        setTokens(null);
        setUser(null);
      } finally {
        setIsReady(true);
      }
    };

    void restoreSession();
  }, []);

  const persistTokens = (nextTokens: TokenPair | null) => {
    setTokens(nextTokens);
    if (nextTokens) {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(nextTokens));
    } else {
      window.localStorage.removeItem(STORAGE_KEY);
    }
  };

  const login = async (email: string, password: string) => {
    try {
      const nextTokens = await loginAdmin(email, password);
      const me = await getCurrentUser(nextTokens.access_token);
      persistTokens(nextTokens);
      setUser(me);
      return me;
    } catch (error) {
      persistTokens(null);
      setUser(null);
      throw error;
    }
  };

  const logout = () => {
    persistTokens(null);
    setUser(null);
  };

  return {
    tokens,
    user,
    isReady,
    isAuthenticated: Boolean(user && tokens?.access_token),
    login,
    logout
  };
}
