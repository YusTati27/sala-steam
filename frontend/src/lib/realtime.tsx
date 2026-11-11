import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { getToken } from "./api";
import { useAuth } from "./auth";

export interface Toast {
  id: number;
  text: string;
  level: "info" | "success" | "error";
}
interface Ctx {
  live: boolean;
  toasts: Toast[];
  push: (text: string, level?: Toast["level"]) => void;
  dismiss: (id: number) => void;
}
const RT = createContext<Ctx | null>(null);

/** Qué consultas se refrescan cuando el servidor avisa que cambió una entidad. */
const MAP: Record<string, string[]> = {
  jobs: ["jobs", "dashboard", "alerts", "equipment"],
  equipment: ["equipment", "dashboard", "alerts"],
  filaments: ["filaments", "dashboard", "alerts"],
  reservations: ["reservations", "dashboard", "alerts"],
  maintenance: ["maintenance", "dashboard", "alerts", "equipment"],
  stats: ["stats", "dashboard"],
};

export function RealtimeProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const qc = useQueryClient();
  const [live, setLive] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const seq = useRef(0);

  const dismiss = useCallback((id: number) => setToasts((t) => t.filter((x) => x.id !== id)), []);
  const push = useCallback(
    (text: string, level: Toast["level"] = "info") => {
      const id = ++seq.current;
      setToasts((t) => [...t.slice(-3), { id, text, level }]);
      setTimeout(() => dismiss(id), 5000);
    },
    [dismiss],
  );

  useEffect(() => {
    if (!user) return;
    let ws: WebSocket | null = null;
    let retry = 0;
    let closed = false;
    let timer: ReturnType<typeof setTimeout>;
    const pending = new Set<string>();
    let flush: ReturnType<typeof setTimeout> | null = null;

    const connect = () => {
      const proto = location.protocol === "https:" ? "wss" : "ws";
      ws = new WebSocket(`${proto}://${location.host}/ws`);
      ws.onopen = () => ws?.send(JSON.stringify({ token: getToken() }));
      ws.onmessage = (ev) => {
        const msg = JSON.parse(ev.data);
        if (msg.type === "ready") {
          setLive(true);
          retry = 0;
          return;
        }
        if (msg.type !== "update") return;
        (msg.entities as string[]).forEach((e) => (e === "all" ? Object.keys(MAP).forEach((k) => pending.add(k)) : pending.add(e)));
        if (msg.message) push(msg.message, msg.level === "error" ? "error" : "info");
        if (msg.entities.includes("all")) qc.invalidateQueries({ queryKey: ["config"] });
        if (!flush)
          flush = setTimeout(() => {
            const keys = new Set<string>();
            pending.forEach((e) => (MAP[e] ?? [e]).forEach((k) => keys.add(k)));
            pending.clear();
            flush = null;
            keys.forEach((k) => qc.invalidateQueries({ queryKey: [k] }));
          }, 400);
      };
      ws.onclose = () => {
        setLive(false);
        if (!closed) timer = setTimeout(connect, Math.min(15000, 1000 * 2 ** retry++));
      };
    };
    connect();
    return () => {
      closed = true;
      clearTimeout(timer);
      if (flush) clearTimeout(flush);
      ws?.close();
      setLive(false);
    };
  }, [user, qc, push]);

  return <RT.Provider value={{ live, toasts, push, dismiss }}>{children}</RT.Provider>;
}

export function useRealtime() {
  const c = useContext(RT);
  if (!c) throw new Error("useRealtime fuera de RealtimeProvider");
  return c;
}
