import * as THREE from "three";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";

// Preview materials for the 3D viewer (also used to render screenshots outside the app).
// Finishes by part name (the GLB's node names are the CAD part keys; a two-tone part's
// lower colour is exported as "<key>_lower"). Anything else keeps its exported colour.
export type Finish = "gloss_black" | "cream" | "red" | "brass" | "frosted" | "opal" | "internal" | "etch_fill";
export const FINISH: Record<string, Finish> = {
  base: "gloss_black", base_plate: "internal", felt_pad: "internal",
  band_cream: "cream", tower: "cream", tower_lower: "red", cap: "red",
  nameplate: "brass", knob: "brass", gallery: "brass", railing: "brass", lantern_frame: "brass", cap_spigot: "brass",
  finial: "brass", nameplate_fill: "etch_fill",
  lantern_glass: "frosted", diffuser: "opal",
};
const GLOW = new THREE.Color("#ffb45e");

export function material(finish: Finish, lit: boolean): THREE.Material {
  switch (finish) {
    case "gloss_black":
      return new THREE.MeshPhysicalMaterial({ color: "#0e0e0e", roughness: 0.22, clearcoat: 1, clearcoatRoughness: 0.04 });
    case "cream":
      return new THREE.MeshPhysicalMaterial({ color: "#f6ecd6", roughness: 0.42, clearcoat: 0.5, clearcoatRoughness: 0.18 });
    case "red":
      return new THREE.MeshPhysicalMaterial({ color: "#7d1913", roughness: 0.4, clearcoat: 0.55, clearcoatRoughness: 0.18 });
    case "brass":
      return new THREE.MeshPhysicalMaterial({ color: "#c9a256", metalness: 1, roughness: 0.27, clearcoat: 0.3, clearcoatRoughness: 0.1 });
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
