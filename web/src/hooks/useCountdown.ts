import { useEffect, useRef, useState } from "react";

/** Contagem regressiva a partir de um valor do servidor (a fonte da verdade do tempo). */
export function useCountdown(initial: number | null, running: boolean, onEnd: () => void): number | null {
  const [left, setLeft] = useState<number | null>(initial);
  const ended = useRef(false);
  const onEndRef = useRef(onEnd);
  onEndRef.current = onEnd;

  useEffect(() => {
    setLeft(initial);
    ended.current = false;
  }, [initial]);

  useEffect(() => {
    if (!running || left === null) return;
    const timer = window.setInterval(() => {
      setLeft((value) => (value === null ? null : Math.max(0, value - 1)));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [running, left === null]);

  useEffect(() => {
    if (left === 0 && !ended.current) {
      ended.current = true;
      onEndRef.current();
    }
  }, [left]);

  return left;
}
