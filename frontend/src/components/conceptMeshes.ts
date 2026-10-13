// Three.js meshes for the Standard Parts builder's shapes (conceptShapes.ShapeSpec), shared by the concept's 3D
// view and the library panel's part preview. Units: mm.
import * as THREE from "three";
import { globeGeometry, PLACEHOLDER_SIZE, type ShapeSpec } from "../conceptShapes";

const SEGMENTS = 64;

/** Meshes for a shape, its bottom at y = 0 and centred on the vertical axis. */
export function geometriesFor(spec: ShapeSpec | null): THREE.BufferGeometry[] {
  const lathe = (pts: [number, number][]) => new THREE.LatheGeometry(pts.map(([x, y]) => new THREE.Vector2(x, y)), SEGMENTS);
  const lift = (g: THREE.BufferGeometry, y: number) => g.translate(0, y, 0);
  if (!spec) return [lift(new THREE.BoxGeometry(PLACEHOLDER_SIZE, PLACEHOLDER_SIZE, PLACEHOLDER_SIZE), PLACEHOLDER_SIZE / 2)];
  switch (spec.shape) {
    case "tube":
    case "ring": {
      const ro = spec.od / 2, ri = spec.id / 2, h = spec.shape === "tube" ? spec.length : spec.thickness;
      if (ri <= 0) return [lift(new THREE.CylinderGeometry(ro, ro, h, SEGMENTS), h / 2)];
      return [lathe([[ri, 0], [ro, 0], [ro, h], [ri, h], [ri, 0]])];
    }
    case "rod":
      return [lift(new THREE.CylinderGeometry(spec.d / 2, spec.d / 2, spec.length, SEGMENTS), spec.length / 2)];
    case "cylinder":
      return [lift(new THREE.CylinderGeometry(spec.d / 2, spec.d / 2, spec.height, SEGMENTS), spec.height / 2)];
    case "disc":
      return [lift(new THREE.CylinderGeometry(spec.d / 2, spec.d / 2, spec.thickness, SEGMENTS), spec.thickness / 2)];
    case "bar":
    case "strip":
      return [lift(new THREE.BoxGeometry(spec.width, spec.length, spec.thickness), spec.length / 2)];
    case "sheet":
      return [lift(new THREE.BoxGeometry(spec.width, spec.thickness, spec.height), spec.thickness / 2)];
    case "box":
      return [lift(new THREE.BoxGeometry(spec.width, spec.height, spec.depth), spec.height / 2)];
    case "dome": {
      // A half-ellipsoid shell, open at the bottom and (if it has one) at the fitter hole on top.
      const r = spec.d / 2, h = spec.height, open = Math.min((spec.opening ?? 0) / 2, r * 0.95);
      const pts: [number, number][] = [];
      for (let i = 0; i <= 32; i++) {
        const t = (i / 32) * (Math.PI / 2);
        const x = r * Math.cos(t);
        if (x < open) {
          pts.push([open, h * Math.sqrt(1 - (open / r) ** 2)]);
          break;
        }
        pts.push([Math.max(x, 0.001), h * Math.sin(t)]);
      }
      return [lathe(pts)];
    }
    case "cone":
      return [lathe([[spec.d_bottom / 2, 0], [Math.max(spec.d_top / 2, 0.001), spec.height]])];
    case "sphere":
      return [lift(new THREE.SphereGeometry(spec.d / 2, 48, 32), spec.d / 2)];
    case "globe": {
      const g = globeGeometry(spec);
      return [
        lathe([[g.nr, 0], [g.nr, spec.neck_height]]),
        lift(new THREE.SphereGeometry(g.r, 48, 32, 0, Math.PI * 2, 0, g.openAngle), g.centre),
      ];
    }
  }
}
