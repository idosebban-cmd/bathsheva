import { useEffect, useState } from "react";
import { api } from "../api";

interface Health {
  status: string;
  code?: string;
  stale?: boolean;
}

/** True when the backend is still running older code than the files on disk (e.g. it was left running during an
 * update): it only loads its code at start-up, so CAD and documents would be built with the old version. A server
 * from before this check existed doesn't report `stale` at all, which also means old code. */
export function useServerStale(): boolean {
  const [stale, setStale] = useState(false);
  useEffect(() => {
    let alive = true;
    const check = () =>
      api
        .get<Health>("/api/health")
        .then((h) => alive && setStale(h.stale !== false))
        .catch(() => undefined);
    check();
    const timer = window.setInterval(check, 30000);
    window.addEventListener("focus", check);
    return () => {
      alive = false;
      window.clearInterval(timer);
      window.removeEventListener("focus", check);
    };
  }, []);
  return stale;
}

export const STALE_MESSAGE =
  "The workbench server is still running the code from before your last update, so CAD, costs and documents are " +
  "built with the old version. Stop the workbench (Ctrl-C in its Terminal window, or close that window) and start it " +
  "again, then regenerate CAD.";
