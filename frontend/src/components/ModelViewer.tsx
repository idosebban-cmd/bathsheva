import { Suspense, useEffect, useMemo, useState } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { Bounds, ContactShadows, Environment, Lightformer, OrbitControls, useBounds, useGLTF } from "@react-three/drei";
import * as THREE from "three";

// Finishes by part name (the GLB's node names are the CAD part keys; a two-tone part's
// lower colour is exported as "<key>_lower"). Anything else keeps its exported colour.
type Finish = "gloss_black" | "cream" | "red" | "brass" | "frosted" | "opal" | "internal";
const FINISH: Record<string, Finish> = {
  base: "gloss_black", base_plate: "internal", felt_pad: "internal",
  band_cream: "cream", tower: "cream", tower_lower: "red", cap: "red",
  nameplate: "brass", knob: "brass", gallery: "brass", railing: "brass", lantern_frame: "brass", cap_spigot: "brass",
  finial: "brass",
  lantern_glass: "frosted", diffuser: "opal",
};
const GLOW = new THREE.Color("#ffb45e");

function material(finish: Finish, lit: boolean): THREE.Material {
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
    default:
      return new THREE.MeshStandardMaterial({ color: "#5a5a5e", roughness: 0.7 });
  }
}

function partName(obj: THREE.Object3D): string | undefined {
  for (let o: THREE.Object3D | null = obj; o; o = o.parent) {
    if (o.name && o.name in FINISH) return o.name;
  }
  return undefined;
}

function Model({ url, lit }: { url: string; lit: boolean }) {
  const { scene } = useGLTF(url);
  const cloned = useMemo(() => scene.clone(true), [scene]);
  useEffect(() => {
    cloned.traverse((obj) => {
      const mesh = obj as THREE.Mesh;
      if (!mesh.isMesh) return;
      const name = partName(mesh);
      if (name) {
        mesh.material = material(FINISH[name], lit);
      } else {
        const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
        for (const m of mats as THREE.MeshStandardMaterial[]) {
          m.side = THREE.DoubleSide;
          if (m.opacity < 1) {
            m.transparent = true;
            m.depthWrite = false;
          }
        }
      }
      mesh.castShadow = true;
    });
  }, [cloned, lit]);
  // The GLB is in metres (glTF convention); the scene works in millimetres.
  return <primitive object={cloned} scale={1000} />;
}

// Camera directions. The GLB is Y-up: CAD front (-Y) faces +Z, CAD right (+X) faces +X.
const VIEWS = {
  three_quarter: [0.62, 0.32, 0.78],
  front: [0, 0.08, 1],
  side: [1, 0.08, 0],
} as const;
type View = keyof typeof VIEWS;

function ViewControls({ view }: { view: View }) {
  const bounds = useBounds();
  const camera = useThree((s) => s.camera);
  useEffect(() => {
    const [x, y, z] = VIEWS[view];
    camera.position.set(x * 900, 150 + y * 900, z * 900);
    camera.lookAt(0, 150, 0);
    bounds.refresh().clip().fit();
  }, [view, bounds, camera]);
  return null;
}

/** Soft studio lighting built from light panels (no network needed). */
function Studio() {
  return (
    <Environment resolution={256} frames={1}>
      <Lightformer form="rect" intensity={2.2} position={[-3, 4, 4]} scale={[6, 4, 1]} />
      <Lightformer form="rect" intensity={1.4} position={[0, 1, 7]} scale={[10, 6, 1]} />
      <Lightformer form="rect" intensity={1.0} position={[-6, 1, 0]} rotation-y={Math.PI / 2} scale={[8, 6, 1]} />
      <Lightformer form="rect" intensity={1.2} position={[5, 2, 2]} scale={[4, 6, 1]} />
      <Lightformer form="rect" intensity={0.9} position={[0, 3, -6]} scale={[8, 3, 1]} />
      <Lightformer form="ring" intensity={0.6} position={[0, 8, 0]} rotation-x={Math.PI / 2} scale={4} />
      <Lightformer form="rect" intensity={0.3} position={[0, -3, 0]} rotation-x={-Math.PI / 2} scale={[10, 10, 1]} color="#d9cfbf" />
    </Environment>
  );
}

/** In-browser preview of a GLB exported by the CAD service (units: mm). */
export default function ModelViewer({ url }: { url: string }) {
  const [lit, setLit] = useState(false);
  const [view, setView] = useState<View>("three_quarter");
  return (
    <div className="viewer">
      <Canvas shadows dpr={[1, 2]} camera={{ position: [420, 260, 520], fov: 30, near: 1, far: 20000 }}
        gl={{ toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 1.15 }}>
        <color attach="background" args={["#efebe4"]} />
        <Studio />
        <ambientLight intensity={0.15} />
        <directionalLight position={[300, 700, 400]} intensity={0.6} castShadow />
        {lit && <pointLight position={[0, 225, 0]} intensity={60000} distance={600} decay={2} color="#ffcf8a" />}
        <Suspense fallback={null}>
          <Bounds fit clip observe margin={1.25} key={url}>
            <Model url={url} lit={lit} />
            <ViewControls view={view} />
          </Bounds>
        </Suspense>
        <ContactShadows position={[0, -2, 0]} opacity={0.45} scale={500} blur={2.6} far={120} resolution={512} />
        <OrbitControls makeDefault />
      </Canvas>
      <div className="viewer-toggle small">
        {(["front", "side", "three_quarter"] as View[]).map((v) => (
          <button key={v} className={`link${view === v ? " active" : ""}`} onClick={() => setView(v)}>
            {v === "three_quarter" ? "¾" : v[0].toUpperCase() + v.slice(1)}
          </button>
        ))}{" "}
        <label>
          <input type="checkbox" checked={lit} onChange={(e) => setLit(e.target.checked)} /> Lights on
        </label>
      </div>
    </div>
  );
}
