import { useEffect, useState } from "react";
import { api, fileUrl, type CadModel, type Part } from "../api";

/** Bodies that are not parts of their own (preview-only splits and fills). */
const EXTRA_LABELS: Record<string, string> = {
  tower_lower: "Tower (red section)",
};

export default function CadDownloads({ model, projectId }: { model: CadModel; projectId: number }) {
  // Part names come from the project's parts list (cad_key = body name), so every product is labelled correctly.
  const [labels, setLabels] = useState<Record<string, string>>({});
  useEffect(() => {
    api
      .get<Part[]>(`/api/projects/${projectId}/parts`)
      .then((parts) => setLabels(Object.fromEntries(parts.filter((p) => p.cad_key).map((p) => [p.cad_key as string, p.name]))))
      .catch(() => setLabels({}));
  }, [projectId]);
  const byPart = new Map<string, Record<string, string>>();
  for (const o of model.outputs) {
    const key = o.part_key ?? "__assembly__";
    byPart.set(key, { ...(byPart.get(key) ?? {}), [o.format]: o.path });
  }
  const asm = byPart.get("__assembly__") ?? {};
  const link = (path: string | undefined, label: string) =>
    path ? (
      <a href={fileUrl(path)} download>
        {label}
      </a>
    ) : null;

  return (
    <div>
      <div className="row">
        <strong>Assembly:</strong> {link(asm.step, "STEP")} {link(asm.stl, "STL")} {link(asm.glb, "GLB")}
        <a href={`/api/projects/${projectId}/cad/models/${model.version}/download.zip`}>All files (.zip)</a>
      </div>
      <table>
        <thead>
          <tr>
            <th>Part</th>
            <th>Size (mm, X × Y × Z)</th>
            <th>Download</th>
          </tr>
        </thead>
        <tbody>
          {[...byPart.entries()]
            .filter(([k]) => k !== "__assembly__")
            .map(([key, files]) => (
              <tr key={key}>
                <td>{labels[key] ?? EXTRA_LABELS[key] ?? key}</td>
                <td className="small">{model.part_info[key]?.size_mm.map((v) => v.toFixed(1)).join(" × ")}</td>
                <td>
                  {link(files.step, "STEP")} {link(files.stl, "STL")}
                </td>
              </tr>
            ))}
        </tbody>
      </table>
    </div>
  );
}
