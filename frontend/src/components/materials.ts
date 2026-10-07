import * as THREE from "three";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";

// Preview materials for the 3D viewer (also used to render screenshots outside the app).
// Finishes by part name (the GLB's node names are the CAD part keys; a two-tone part's
// lower colour is exported as "<key>_lower"). Anything else keeps its exported colour.
export type Finish = "satin_black" | "cream" | "red" | "brass" | "frosted" | "opal" | "internal" | "etch_fill";
export const FINISH: Record<string, Finish> = {
  base: "satin_black", base_plate: "internal", felt_pad: "internal",
  band_cream: "cream", tower: "cream", tower_lower: "red", cap: "red",
  nameplate: "brass", knob: "brass", gallery: "brass", railing: "brass", lantern_frame: "brass", cap_spigot: "brass",
  finial: "brass", nameplate_fill: "etch_fill", knob_logo_fill: "etch_fill",
  lantern_glass: "frosted", diffuser: "opal",
};
const GLOW = new THREE.Color("#ffb45e");

// Design reference colours (the RFQ's hex values) and gloss levels: base satin black 30–50 GU, cream and oxblood
// red gloss 80+ GU, brass brushed (satin grain) and clear-lacquered like Atelier.
const BLACK = "#121212", CREAM = "#f9f2e1", RED = "#8a1c15", BRASS = "#c4a15a";

/** Brushed grain without UVs: fine horizontal streaks in the roughness, keyed to world height (mm). */
function brushed(m: THREE.MeshPhysicalMaterial): THREE.MeshPhysicalMaterial {
  m.onBeforeCompile = (shader) => {
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", "#include <common>\nvarying vec3 vBrushPos;")
      .replace("#include <project_vertex>", "#include <project_vertex>\nvBrushPos = (modelMatrix * vec4(transformed, 1.0)).xyz;");
    shader.fragmentShader = shader.fragmentShader
      .replace("#include <common>",
        "#include <common>\nvarying vec3 vBrushPos;\nfloat brushHash(float n) { return fract(sin(n) * 43758.5453); }")
      .replace("#include <roughnessmap_fragment>",
        "#include <roughnessmap_fragment>\n" +
        "float bl = vBrushPos.y * 18.0 + sin(atan(vBrushPos.z, vBrushPos.x) * 3.0) * 0.6;\n" +
        "float grain = 0.6 * brushHash(floor(bl)) + 0.4 * brushHash(floor(bl * 0.31) + 7.0);\n" +
        "roughnessFactor = clamp(roughnessFactor + (grain - 0.5) * 0.16, 0.05, 1.0);");
  };
  m.customProgramCacheKey = () => "brushed";
  return m;
}

export function material(finish: Finish, lit: boolean): THREE.Material {
  switch (finish) {
    case "satin_black": // 30–50 GU: soft, broad reflections
      return new THREE.MeshPhysicalMaterial({ color: BLACK, roughness: 0.48, clearcoat: 0.35, clearcoatRoughness: 0.38 });
    case "cream": // 80+ GU gloss
      return new THREE.MeshPhysicalMaterial({ color: CREAM, roughness: 0.2, clearcoat: 1, clearcoatRoughness: 0.05 });
    case "red": // 80+ GU gloss
      return new THREE.MeshPhysicalMaterial({ color: RED, roughness: 0.2, clearcoat: 1, clearcoatRoughness: 0.05 });
    case "brass": // brushed satin, clear lacquer
      return brushed(new THREE.MeshPhysicalMaterial({ color: BRASS, metalness: 1, roughness: 0.36, clearcoat: 0.45,
        clearcoatRoughness: 0.12 }));
    case "frosted":
      return new THREE.MeshPhysicalMaterial({
        color: "#fbf6ec", roughness: 0.55, transmission: lit ? 0.2 : 0.85, thickness: 2, ior: 1.47,
        emissive: lit ? GLOW : new THREE.Color(0), emissiveIntensity: lit ? 2.2 : 0, side: THREE.DoubleSide,
      });
    case "opal":
      return new THREE.MeshPhysicalMaterial({
        color: "#f7f1e6", roughness: 0.7, transmission: 0.25, thickness: 2, ior: 1.47,
        emissive: lit ? GLOW : new THREE.Color(0), emissiveIntensity: lit ? 2.6 : 0, side: THREE.DoubleSide,
      });
    case "etch_fill":
      return new THREE.MeshStandardMaterial({ color: "#050505", roughness: 0.9 });
    default:
      return new THREE.MeshStandardMaterial({ color: "#5a5a5e", roughness: 0.7 });
  }
}


// Parts whose curved faces are flat facets in the CAD (the nameplate: 0.5° facets round the lamp axis, so
// its etched lettering cuts reliably). The GLB holds one mesh per CAD face; merge the part's meshes and give
// the curved faces the true cylinder normal (radial from the lamp axis, which is world Y), so the brass shades
// smoothly. Faces that aren't on the cylinder (the letter walls, the plate edges) keep their own normals.
const FACETED = ["nameplate"];
const ON_CYLINDER = Math.cos(THREE.MathUtils.degToRad(25));

export function smoothFaceted(root: THREE.Object3D) {
  root.updateMatrixWorld(true);
  for (const name of FACETED) {
    const node = root.getObjectByName(name);
    if (!node || node.userData.smoothed) continue;
    const meshes: THREE.Mesh[] = [];
    node.traverse((o) => {
      if ((o as THREE.Mesh).isMesh) meshes.push(o as THREE.Mesh);
    });
    if (!meshes.length) continue;
    const geoms = meshes.map((m) => {
      const g = m.geometry.index ? m.geometry.toNonIndexed() : m.geometry.clone();
      for (const key of Object.keys(g.attributes)) if (key !== "position" && key !== "normal") g.deleteAttribute(key);
      if (!g.attributes.normal) g.computeVertexNormals();
      return g.applyMatrix4(m.matrixWorld); // world space: the lamp axis is the world Y axis
    });
    const merged = mergeGeometries(geoms, false);
    if (!merged) continue;
    const pos = merged.attributes.position, nrm = merged.attributes.normal;
    const p = new THREE.Vector3(), n = new THREE.Vector3(), r = new THREE.Vector3();
    for (let i = 0; i < pos.count; i++) {
      p.fromBufferAttribute(pos, i);
      n.fromBufferAttribute(nrm, i).normalize();
      r.set(p.x, 0, p.z).normalize();
      const d = n.dot(r);
      if (d > ON_CYLINDER) nrm.setXYZ(i, r.x, r.y, r.z);
      else if (d < -ON_CYLINDER) nrm.setXYZ(i, -r.x, -r.y, -r.z);
    }
    merged.applyMatrix4(new THREE.Matrix4().copy(node.matrixWorld).invert());
    const mesh = new THREE.Mesh(merged, meshes[0].material);
    mesh.name = `${name}_smoothed`;
    for (const m of meshes) m.parent?.remove(m);
    node.add(mesh);
    node.userData.smoothed = true;
  }
}
