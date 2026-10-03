"use client";

import { useCallback, useEffect, useState } from "react";

/** Seconds-remaining timer, e.g. for "resend code" cooldowns. */
export function useCountdown(initialSeconds = 0) {
  const [seconds, setSeconds] = useState(initialSeconds);

  useEffect(() => {
    if (seconds <= 0) return;
    const timer = setTimeout(() => setSeconds((s) => s - 1), 1000);
    return () => clearTimeout(timer);
  }, [seconds]);

  const start = useCallback((value: number) => setSeconds(value), []);
  return { seconds, active: seconds > 0, start };
}
