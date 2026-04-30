"use client";

import { useEffect, useState } from "react";

import { getCurrentUser, loginAdmin } from "@/shared/api/browser-client";
import type { TokenPair, User } from "@/shared/api/types";
import { browserAdminTokenStore } from "@/shared/auth/adminTokenStore";

export function useAdminAuth() {
  const [tokens, setTokens] = useState<TokenPair | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    const restoreSession = async () => {
      const parsed = browserAdminTokenStore.readTokenPair();
      if (!parsed) {
        setIsReady(true);
        return;
      }

      try {
        const me = await getCurrentUser(parsed.access_token);
        setTokens(parsed);
        setUser(me);
      } catch {
        browserAdminTokenStore.clear();
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
    browserAdminTokenStore.writeTokenPair(nextTokens);
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
