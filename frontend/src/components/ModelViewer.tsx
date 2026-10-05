import { Suspense, useEffect, useMemo } from "react";
import { Canvas } from "@react-three/fiber";
import { Bounds, OrbitControls, useGLTF } from "@react-three/drei";
import * as THREE from "three";

function Model({ url }: { url: string }) {
  const { scene } = useGLTF(url);
  const cloned = useMemo(() => scene.clone(true), [scene]);
  useEffect(() => {
    cloned.traverse((obj) => {
      const mesh = obj as THREE.Mesh;
      if (!mesh.isMesh) return;
      const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
      for (const m of mats as THREE.MeshStandardMaterial[]) {
        m.side = THREE.DoubleSide;
        m.metalness = Math.min(m.metalness ?? 0, 0.3);
        m.roughness = Math.max(m.roughness ?? 0.5, 0.35);
        if (m.opacity < 1) {
          m.transparent = true;
          m.depthWrite = false;
        }
      }
    });
  }, [cloned]);
  return <primitive object={cloned} />;
}

/** In-browser preview of a GLB exported by the CAD service (units: mm). */
export default function ModelViewer({ url }: { url: string }) {
  return (
    <div className="viewer">
      <Canvas camera={{ position: [400, 300, 500], fov: 35, near: 1, far: 20000 }}>
        <color attach="background" args={["#efece6"]} />
        <ambientLight intensity={0.7} />
        <directionalLight position={[300, 600, 400]} intensity={1.6} />
        <directionalLight position={[-400, 200, -300]} intensity={0.6} />
        <hemisphereLight args={["#ffffff", "#bbb3a5", 0.5]} />
        <Suspense fallback={null}>
          <Bounds fit clip observe margin={1.3} key={url}>
            <Model url={url} />
          </Bounds>
        </Suspense>
        <gridHelper args={[1000, 20, "#c9c3b8", "#ddd8cf"]} />
        <OrbitControls makeDefault />
      </Canvas>
    </div>
  );
}
