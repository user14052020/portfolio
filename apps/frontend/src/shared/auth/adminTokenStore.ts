import type { TokenPair } from "@/shared/api/types";

export const ADMIN_TOKENS_STORAGE_KEY = "portfolio-admin-tokens";

export interface AccessTokenProvider {
  getAccessToken(): string | null;
}

export interface AdminTokenStore extends AccessTokenProvider {
  readTokenPair(): TokenPair | null;
  writeTokenPair(tokens: TokenPair | null): void;
  clear(): void;
}

export class BrowserAdminTokenStore implements AdminTokenStore {
  constructor(private readonly storageKey = ADMIN_TOKENS_STORAGE_KEY) {}

  getAccessToken(): string | null {
    return this.readTokenPair()?.access_token ?? null;
  }

  readTokenPair(): TokenPair | null {
    const raw = this.readRawValue();
    if (!raw) {
      return null;
    }

    try {
      const parsed = JSON.parse(raw) as unknown;
      const tokens = this.normalizeTokenPair(parsed);
      if (!tokens) {
        this.clear();
      }
      return tokens;
    } catch {
      this.clear();
      return null;
    }
  }

  writeTokenPair(tokens: TokenPair | null): void {
    if (!tokens) {
      this.clear();
      return;
    }

    const storage = this.getStorage();
    if (!storage) {
      return;
    }

    try {
      storage.setItem(this.storageKey, JSON.stringify(tokens));
    } catch {
      // Storage may be blocked; auth still works for the current in-memory hook state.
    }
  }

  clear(): void {
    const storage = this.getStorage();
    if (!storage) {
      return;
    }

    try {
      storage.removeItem(this.storageKey);
    } catch {
      // Ignore blocked storage cleanup.
    }
  }

  private readRawValue(): string | null {
    const storage = this.getStorage();
    if (!storage) {
      return null;
    }

    try {
      return storage.getItem(this.storageKey);
    } catch {
      return null;
    }
  }

  private getStorage(): Storage | null {
    if (typeof window === "undefined") {
      return null;
    }

    try {
      return window.localStorage;
    } catch {
      return null;
    }
  }

  private normalizeTokenPair(value: unknown): TokenPair | null {
    if (!value || typeof value !== "object") {
      return null;
    }

    const candidate = value as Partial<TokenPair>;
    if (
      typeof candidate.access_token !== "string" ||
      !candidate.access_token.trim() ||
      typeof candidate.refresh_token !== "string" ||
      typeof candidate.token_type !== "string"
    ) {
      return null;
    }

    return {
      access_token: candidate.access_token,
      refresh_token: candidate.refresh_token,
      token_type: candidate.token_type,
    };
  }
}

export const browserAdminTokenStore = new BrowserAdminTokenStore();
