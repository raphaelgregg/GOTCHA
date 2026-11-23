import { useCallback, useEffect, useRef, useState } from "react";

export interface AsyncState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  reload: () => void;
  setData: (value: T | null) => void;
}

/** Carrega dados assíncronos e expõe recarregar; evita atualizar estado depois de desmontar. */
export function useAsync<T>(loader: () => Promise<T>, deps: unknown[] = []): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [version, setVersion] = useState(0);
  const alive = useRef(true);

  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);

  useEffect(() => {
    let current = true;
    setLoading(true);
    loader()
      .then((value) => current && alive.current && (setData(value), setError(null)))
      .catch((e: unknown) => current && alive.current && setError(messageOf(e)))
      .finally(() => current && alive.current && setLoading(false));
    return () => {
      current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [version, ...deps]);

  const reload = useCallback(() => setVersion((v) => v + 1), []);
  return { data, error, loading, reload, setData };
}

export function messageOf(e: unknown): string {
  return e instanceof Error ? e.message : "Algo deu errado.";
}
