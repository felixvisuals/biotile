import { useEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import { useTranslation } from "react-i18next";
import { useClickToActivate } from "./useClickToActivate";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { decodeHeights, type Preview } from "../api";

// Muted, paper-like material tints (the page itself is monochrome).
const MATERIAL_COLORS: Record<string, number> = {
  clay: 0xe2d6cc,
  concrete: 0xd9d8d2,
  lime: 0xeeebe2,
  loam: 0xdcd2c2,
};

/** Grid surface: z per node (row 0 = top), NaN = outside the tile (no triangles there). */
function gridGeometry(z: Float32Array, nx: number, ny: number, w: number, h: number): THREE.BufferGeometry {
  const pos = new Float32Array(nx * ny * 3);
  for (let i = 0; i < ny; i++) {
    for (let j = 0; j < nx; j++) {
      const k = i * nx + j;
      pos[3 * k] = ((j + 0.5) / nx - 0.5) * w;
      pos[3 * k + 1] = (0.5 - (i + 0.5) / ny) * h;
      const v = z[k];
      pos[3 * k + 2] = Number.isFinite(v) ? v : 0;
    }
  }
  const idx: number[] = [];
  const ok = (k: number) => Number.isFinite(z[k]);
  for (let i = 0; i < ny - 1; i++) {
    for (let j = 0; j < nx - 1; j++) {
      const a = i * nx + j, b = a + 1, c = a + nx, d = c + 1;
      if (ok(a) && ok(b) && ok(c)) idx.push(c, b, a);
      if (ok(b) && ok(c) && ok(d)) idx.push(c, d, b);
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  g.setIndex(idx);
  g.computeVertexNormals();
  return g;
}

type Props = { preview: Preview; view: "one" | "wall"; className?: string; compact?: boolean };

const NO_REF = { current: null };

export default function ReliefViewer({ preview, view, className, compact = false }: Props) {
  const { t } = useTranslation();
  const mountRef = useRef<HTMLDivElement>(null);
  const stateRef = useRef<{
    renderer: THREE.WebGLRenderer; scene: THREE.Scene; camera: THREE.PerspectiveCamera;
    controls: OrbitControls; group: THREE.Group; raf: number;
  } | null>(null);
  const front = useMemo(() => decodeHeights(preview.front.b64), [preview.front.b64]);
  const wall = useMemo(() => decodeHeights(preview.wall.b64), [preview.wall.b64]);

  // one-time setup
  useEffect(() => {
    const el = mountRef.current!;
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x000000, 0);
    el.appendChild(renderer.domElement);
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(35, 1, 1, 6000);
    // The tile lies in the x/y plane, its front looks along +z. "Up" must be set BEFORE the
    // controls are created, otherwise OrbitControls orbits around the wrong axis (the cause
    // of the odd tumbling and of ending up behind the tile).
    camera.up.set(0, 0, 1);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.rotateSpeed = 0.7;
    controls.minPolarAngle = 0; // straight on
    controls.maxPolarAngle = THREE.MathUtils.degToRad(70); // never edge-on or behind: the front stays in view
    controls.enablePan = false;
    scene.add(new THREE.HemisphereLight(0xffffff, 0x9a968c, 1.4));
    const sun = new THREE.DirectionalLight(0xffffff, 1.9);
    sun.position.set(-200, 260, 320); // raking light from top-left reveals the relief
    scene.add(sun);
    const group = new THREE.Group();
    scene.add(group);
    if (compact) {
      // Inside a scrolling page the tile is passive until clicked (see useClickToActivate):
      // a disabled OrbitControls ignores wheel and touch, so the page scrolls on undisturbed.
      controls.enabled = false;
      renderer.domElement.style.touchAction = "pan-y";
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
    }
    const resize = () => {
      renderer.setSize(el.clientWidth, el.clientHeight);
      camera.aspect = el.clientWidth / Math.max(el.clientHeight, 1);
      camera.updateProjectionMatrix();
    };
    const ro = new ResizeObserver(resize);
    ro.observe(el);
    resize();
    const tick = () => {
      controls.update();
      renderer.render(scene, camera);
      stateRef.current!.raf = requestAnimationFrame(tick);
    };
    stateRef.current = { renderer, scene, camera, controls, group, raf: 0 };
    tick();
    return () => {
      cancelAnimationFrame(stateRef.current!.raf);
      ro.disconnect();
      controls.dispose();
      renderer.dispose();
      el.removeChild(renderer.domElement);
      stateRef.current = null;
    };
  }, []);

  // camera framing: depends on the view and the tile size only
  const extent = view === "wall" ? preview.wall.extent_mm : Math.max(...preview.bbox_mm);
  useEffect(() => {
    const s = stateRef.current;
    if (!s) return;
    const dist = ((extent * 0.5) / Math.tan(THREE.MathUtils.degToRad(s.camera.fov / 2))) * (compact ? 1.25 : 1.4);
    s.camera.position.set(0, -dist * 0.55, dist * 0.84);
    s.controls.target.set(0, 0, -8);
    s.controls.minDistance = dist * 0.3;
    s.controls.maxDistance = dist * 2.2;
    s.controls.update();
  }, [extent, view, compact]);

  // geometry
  useEffect(() => {
    const s = stateRef.current;
    if (!s) return;
    s.group.children.forEach((c) => {
      const m = c as THREE.Mesh;
      m.geometry?.dispose();
      (m.material as THREE.Material)?.dispose();
    });
    s.group.clear();
    const color = MATERIAL_COLORS[preview.params.material] ?? 0xe2d6cc;
    const mat = new THREE.MeshStandardMaterial({ color, roughness: 0.95, metalness: 0, side: THREE.DoubleSide });
    if (view === "one") {
      const [w, h] = preview.bbox_mm;
      s.group.add(new THREE.Mesh(gridGeometry(front, preview.front.nx, preview.front.ny, w, h), mat));
    } else {
      const n = preview.wall.n;
      const e = preview.wall.extent_mm;
      s.group.add(new THREE.Mesh(gridGeometry(wall, n, n, e, e), mat));
      const pts: THREE.Vector3[] = [];
      const half = e / 2;
      for (const line of preview.joints) {
        for (let k = 0; k < line.length - 1; k++) {
          const [x1, y1] = line[k];
          const [x2, y2] = line[k + 1];
          if (Math.max(Math.abs(x1), Math.abs(y1), Math.abs(x2), Math.abs(y2)) > half + 1) continue;
          pts.push(new THREE.Vector3(x1, y1, 0.8), new THREE.Vector3(x2, y2, 0.8));
        }
      }
      s.group.add(new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(pts),
        new THREE.LineBasicMaterial({ color: 0x222222, transparent: true, opacity: 0.3 })));
    }
  }, [front, wall, preview, view]);

  const active = useClickToActivate(compact ? mountRef : NO_REF, (v) => {
    const s = stateRef.current;
    if (s) {
      s.controls.enabled = v;
      s.renderer.domElement.style.touchAction = v ? "none" : "pan-y";
    }
  });

  // data-lenis-prevent: the wheel zooms the model instead of scrolling the page
  return compact
    ? (
      <div ref={mountRef} className={`group ${className ?? "h-[420px] w-full"}`}>
        {!active && (
          <span className="pointer-events-none absolute bottom-3 left-1/2 z-10 -translate-x-1/2 whitespace-nowrap rounded-full bg-bg/80 px-3 py-1 font-mono text-[10px] uppercase tracking-widest opacity-0 transition-opacity group-hover:opacity-70">
            {t("common.click_to_turn")}
          </span>
        )}
      </div>
    )
    : <div ref={mountRef} data-lenis-prevent className={className ?? "h-[420px] w-full"} />;
}
