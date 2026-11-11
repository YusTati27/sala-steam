import { useMutation, useQuery, useQueryClient, type QueryKey } from "@tanstack/react-query";
import { api } from "./api";
import { useRealtime } from "./realtime";
import type { Config } from "./types";

type Params = Record<string, string | number | boolean | undefined | null>;

/** Consulta GET con clave [entidad, ...]; la entidad se invalida desde WebSocket. */
export function useGet<T>(entity: string, path: string, params?: Params, extra: unknown[] = [], enabled = true) {
  return useQuery<T>({
    queryKey: [entity, path, params ?? {}, ...extra] as QueryKey,
    queryFn: () => api<T>(path, { params }),
    enabled,
  });
}

export const useConfig = () => useGet<Config>("config", "/config");

/** Mutación con aviso de éxito/error y refresco de las entidades indicadas. */
export function useAction<TIn = void, TOut = unknown>(
  fn: (input: TIn) => Promise<TOut>,
  opts: { invalidate?: string[]; success?: string; onSuccess?: (out: TOut) => void } = {},
) {
  const qc = useQueryClient();
  const { push } = useRealtime();
  return useMutation<TOut, Error, TIn>({
    mutationFn: fn,
    onSuccess: (out) => {
      (opts.invalidate ?? []).forEach((k) => qc.invalidateQueries({ queryKey: [k] }));
      if (opts.success) push(opts.success, "success");
      opts.onSuccess?.(out);
    },
    onError: (e) => push(e.message, "error"),
  });
}
