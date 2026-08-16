const STORAGE_KEY = "microtune_visitor_id";

export function getOrCreateVisitorId(): string {
  try {
    const existing = localStorage.getItem(STORAGE_KEY);
    if (existing) return existing;

    const id = crypto.randomUUID();
    localStorage.setItem(STORAGE_KEY, id);
    return id;
  } catch {
    // localStorage unavailable (privacy mode, SSR, etc.) — fall back to an ephemeral id.
    return crypto.randomUUID();
  }
}
