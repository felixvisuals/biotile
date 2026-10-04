import { useEffect, useRef } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { mergeVertices } from "three/examples/jsm/utils/BufferGeometryUtils.js";

/**
 * Hexagonal relief tile after Gaudí's paving tile (homage, own geometry).
 *
 * Seamless by construction: the height is a function of the hexagonal lattice only.
 *   h(x) = max( S(x - c),  A(x - a_i),  B(x - b_i) )
 * c = tile centre (starfish), a_i / b_i = the two vertex sublattices of the honeycomb
 * (ammonite / sargassum alga). Every vertex is shared by three tiles, so each tile carries
 * one third of those figures; because all tiles are pure translates of each other and every
 * motif stays inside its support radius (< side length), neighbouring tiles agree exactly
 * along each edge. No smoothing or blending at the seams is needed.
 */

const A = 1; // hexagon side (flat-top); everything below is in units of A
const H = 0.09; // relief height

const smooth = (e0: number, e1: number, x: number) => {
  const t = Math.min(1, Math.max(0, (x - e0) / (e1 - e0)));
  return t * t * (3 - 2 * t);
};

function starfish(x: number, y: number) {
  const r = Math.hypot(x, y);
  if (r > 0.42) return 0;
  const th = Math.atan2(y, x) + Math.PI / 2;
  const arm = 0.42 * (0.28 + 0.72 * Math.pow(Math.abs(Math.cos(2.5 * th)), 2.2));
  const body = 1 - smooth(arm * 0.82, arm, r);
  const ridge = 0.25 * Math.pow(Math.abs(Math.cos(2.5 * th)), 8) * (1 - r / 0.42);
  return H * (0.75 * body + ridge * body);
}

function ammonite(x: number, y: number) {
  const r = Math.hypot(x, y);
  const R = 0.5;
  if (r > R || r < 1e-4) return 0;
  const th = Math.atan2(y, x);
  // logarithmic spiral whorls: r = r0 * e^(b θ)
  const b = 0.18;
  const phase = (Math.log(r / 0.02) / b - th) / (2 * Math.PI);
  const whorl = Math.pow(Math.abs(Math.cos(Math.PI * phase)), 0.6);
  const ribs = 0.15 * Math.max(0, Math.cos(th * 22));
  return H * (0.55 + 0.35 * whorl + ribs * whorl) * (1 - smooth(R * 0.88, R, r));
}

// sargassum: a curved stem with alternating leaves and small air bladders
const ALGA: [number, number, number][] = [];
for (let i = 0; i <= 24; i++) {
  const t = i / 24;
  const x = -0.38 + 0.76 * t;
  const y = 0.16 * Math.sin(t * Math.PI * 1.6);
  ALGA.push([x, y, 0.035]);
  if (i % 4 === 2) {
    const s = i % 8 === 2 ? 1 : -1;
    ALGA.push([x + 0.03, y + s * 0.09, 0.055]); // leaf
    ALGA.push([x + 0.06, y + s * 0.16, 0.025]); // bladder
  }
}
function sargassum(x: number, y: number) {
  if (Math.hypot(x, y) > 0.5) return 0;
  let best = 0;
  for (const [cx, cy, rad] of ALGA) {
    const d = Math.hypot(x - cx, y - cy);
    best = Math.max(best, 1 - smooth(rad * 0.6, rad, d));
  }
  return H * 0.85 * best;
}

const VA = [0, 2, 4].map((k) => [Math.cos((k * Math.PI) / 3), Math.sin((k * Math.PI) / 3)]);
const VB = [1, 3, 5].map((k) => [Math.cos((k * Math.PI) / 3), Math.sin((k * Math.PI) / 3)]);

export function hexHeight(x: number, y: number) {
  let h = starfish(x, y);
  for (const [vx, vy] of VA) h = Math.max(h, ammonite(x - vx, y - vy));
  for (const [vx, vy] of VB) h = Math.max(h, sargassum(x - vx, y - vy));
  return h;
}

function hexGeometry(n: number): THREE.BufferGeometry {
  // 6 sectors (centre, V_k, V_k+1), each subdivided into n^2 triangles: an exact hexagon.
  const pos: number[] = [];
  const corners = Array.from({ length: 6 }, (_, k) => [A * Math.cos((k * Math.PI) / 3), A * Math.sin((k * Math.PI) / 3)]);
  const P = (u: number, v: number, k: number) => {
    const [x1, y1] = corners[k];
    const [x2, y2] = corners[(k + 1) % 6];
    const x = (u * x1 + v * x2) / n;
    const y = (u * y1 + v * y2) / n;
    return [x, y, hexHeight(x, y)];
  };
  for (let k = 0; k < 6; k++) {
    for (let i = 0; i < n; i++) {
      for (let j = 0; j < n - i; j++) {
        pos.push(...P(i, j, k), ...P(i + 1, j, k), ...P(i, j + 1, k));
        if (j < n - i - 1) pos.push(...P(i + 1, j, k), ...P(i + 1, j + 1, k), ...P(i, j + 1, k));
      }
    }
  }
  let g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  g = mergeVertices(g, 1e-5);
  g.computeVertexNormals();
  return g;
}

export default function HexRelief({ cluster, className, sway = false }: { cluster: boolean; className?: string; sway?: boolean }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = ref.current!;
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    el.appendChild(renderer.domElement);
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(32, 1, 0.01, 100);
    camera.up.set(0, 0, 1);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.maxPolarAngle = THREE.MathUtils.degToRad(70); // keep the front in view
    controls.enablePan = false;
    scene.add(new THREE.HemisphereLight(0xffffff, 0x9a968c, 1.3));
    const sun = new THREE.DirectionalLight(0xffffff, 2.0);
    sun.position.set(-3, 4, 5);
    scene.add(sun);
    const geo = hexGeometry(70);
    const mat = new THREE.MeshStandardMaterial({ color: 0xd9d8d2, roughness: 0.95 });
    // flat-top hex lattice: centres at i*(1.5, √3/2) + j*(0, √3)
    const centres: [number, number][] = [[0, 0]];
    if (cluster) {
      for (let k = 0; k < 6; k++) {
        const a = (k * Math.PI) / 3 + Math.PI / 6;
        centres.push([Math.sqrt(3) * Math.cos(a), Math.sqrt(3) * Math.sin(a)]);
      }
    }
    for (const [cx, cy] of centres) {
      const m = new THREE.Mesh(geo, mat);
      m.position.set(cx, cy, 0);
      scene.add(m);
    }
    const dist = cluster ? 10.5 : 5.4;
    camera.position.set(0, -dist * 0.55, dist * 0.84);
    controls.target.set(0, 0, 0);
    const resize = () => {
      renderer.setSize(el.clientWidth, el.clientHeight);
      camera.aspect = el.clientWidth / Math.max(1, el.clientHeight);
      camera.updateProjectionMatrix();
    };
    const ro = new ResizeObserver(resize);
    ro.observe(el);
    resize();
    // Gentle back-and-forth sway of the tiles; stops as soon as the user grabs the model.
    const group = new THREE.Group();
    scene.children.filter((c) => c instanceof THREE.Mesh).forEach((m) => group.add(m));
    scene.add(group);
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let swaying = sway && !reduce;
    controls.addEventListener("start", () => { swaying = false; });
    const t0 = performance.now();
    let raf = 0;
    const tick = () => {
      if (swaying) {
        const t = (performance.now() - t0) / 1000;
        group.rotation.z = Math.sin(t * 0.45) * 0.22;
        group.rotation.x = Math.sin(t * 0.3) * 0.06;
      }
      controls.update();
      renderer.render(scene, camera);
      raf = requestAnimationFrame(tick);
    };
    tick();
    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      controls.dispose();
      geo.dispose();
      mat.dispose();
      renderer.dispose();
      el.removeChild(renderer.domElement);
    };
  }, [cluster, sway]);
  return <div ref={ref} data-lenis-prevent className={className ?? "aspect-square w-full"} />;
}
