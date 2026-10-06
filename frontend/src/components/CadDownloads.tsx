import { fileUrl, type CadModel } from "../api";

const LABELS: Record<string, string> = {
  base: "Base",
  base_plate: "Bottom plate",
  felt_pad: "Felt pad",
  weight_plate: "Weight plate",
  nameplate: "Nameplate",
  band_cream: "Cream band",
  tower: "Tower",
  diffuser: "Window diffuser",
  tower_light: "Tower light",
  dimmer: "Dimmer",
  knob: "Dimmer knob",
  gallery: "Gallery",
  railing: "Gallery railing",
  lantern_frame: "Lantern frame",
  lantern_glass: "Lantern glass",
  led_module: "Lantern LED",
  cap: "Cap",
  cap_spigot: "Cap bayonet spigot",
  finial: "Finial",
  battery: "Battery pack",
  charge_board: "Control board",
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
