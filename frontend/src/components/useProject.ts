import { useOutletContext } from "react-router-dom";
import type { Project } from "../api";

export interface ProjectContext {
  project: Project;
  reload: () => Promise<void>;
}

export function useProject(): ProjectContext {
  return useOutletContext<ProjectContext>();
}
