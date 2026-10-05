import { fileUrl, type CadModel } from "../api";

const LABELS: Record<string, string> = {
  base: "Base",
  main_body: "Main body",
  band: "Decorative band",
  lantern: "Lantern",
  top_cap: "Top cap",
  led_module: "LED module",
  cable: "Cable / power entry",
};

export default function CadDownloads({ model, projectId }: { model: CadModel; projectId: number }) {
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
                <td>{LABELS[key] ?? key}</td>
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
