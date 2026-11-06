// 高画質ビュー。既定の自前WebGLとは別のキャンバスに three.js で描く。
//
// 形は既存のエンジンがつくる faces をそのまま使う（図面から起こした寸法が唯一の正解で、
// ここで作り直したりはしない）。変えるのは光と質感だけ：
//   * RoomEnvironment を環境光にして、面ごとの一様な明るさをやめる
//   * 下り天井のスリットに実際の光源を置く
//   * ガラス面から入る昼光を影つきで入れる
//   * ACES のトーンマッピングと sRGB 出力
//
// 読み込みに失敗しても既定の描画は動き続ける（index.html は type="module" で読むだけ）。
import * as THREE from './vendor/three.min.js';

const WARM = 0xffd2a1;          // 3500K 相当。設備図の器具リストに合わせている。
const DAY  = 0xdfeaf2;

let renderer, scene, camera, solid, glass, env, group, lights;

function toLinear(hex) {
  return new THREE.Color().setStyle(hex, THREE.SRGBColorSpace);
}

// faces -> 非インデックスの BufferGeometry。三角形ごとに法線が立つので、
// computeVertexNormals() がそのままフラットシェーディングになる。
function geometry(faces) {
  const pos = [], col = [], c = new THREE.Color();
  for (const f of faces) {
    c.copy(toLinear(f.c));
    for (let i = 1; i < f.v.length - 1; i++)
      for (const p of [f.v[0], f.v[i], f.v[i + 1]]) {
        pos.push(p[0], p[1], p[2]);
        col.push(c.r, c.g, c.b);
      }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
  g.computeVertexNormals();
  return g;
}

function init(canvas) {
  renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 0.78;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;

  scene = new THREE.Scene();
  scene.background = new THREE.Color(0xf1efe8);
  camera = new THREE.PerspectiveCamera(60, 1, 0.05, 120);

  // 室内の相互反射のかわり。これが無いと影の側が真っ黒になる。
  const pmrem = new THREE.PMREMGenerator(renderer);
  env = pmrem.fromScene(new THREE.RoomEnvironment(), 0.04).texture;
  scene.environment = env;
  scene.environmentIntensity = 0.42;

  group = new THREE.Group();
  scene.add(group);
  lights = new THREE.Group();
  scene.add(lights);
  return true;
}

// 下り天井のスリットに置く光。coves は [x0,z0,x1,z1,y] の配列。
function placeCoves(coves) {
  for (const [x0, z0, x1, z1, y] of coves) {
    const len = Math.hypot(x1 - x0, z1 - z0);
    const n = Math.max(2, Math.min(6, Math.round(len / 1.2)));
    for (let i = 0; i < n; i++) {
      const t = (i + 0.5) / n;
      const l = new THREE.PointLight(WARM, 1.9, 4.0, 2);
      l.position.set(x0 + (x1 - x0) * t, y - 0.12, z0 + (z1 - z0) * t);
      lights.add(l);
    }
  }
}

function build(faces, glassFaces, coves, opts) {
  group.clear();
  lights.clear();

  solid = new THREE.Mesh(geometry(faces), new THREE.MeshStandardMaterial({
    vertexColors: true, roughness: 0.82, metalness: 0.0,
    side: THREE.DoubleSide,
    // 既存エンジンは薄い板を壁に密着させて置くので、Zファイティングを抑える。
    polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1,
  }));
  solid.castShadow = solid.receiveShadow = true;
  group.add(solid);

  if (glassFaces.length) {
    glass = new THREE.Mesh(geometry(glassFaces), new THREE.MeshPhysicalMaterial({
      vertexColors: true, roughness: 0.08, metalness: 0,
      transparent: true, opacity: 0.22, transmission: 0.6, side: THREE.DoubleSide,
    }));
    group.add(glass);
  }

  placeCoves(coves);

  // 昼光。ガラス面のある南西から。室内なので強すぎないように。
  const sun = new THREE.DirectionalLight(DAY, 0.6);
  sun.position.set(-6, 7, 16);
  sun.target.position.set(opts.plan[0] / 2, 0, opts.plan[1] / 2);
  sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048);
  const s = sun.shadow.camera;
  s.left = -14; s.right = 14; s.top = 14; s.bottom = -14; s.near = 1; s.far = 40;
  sun.shadow.bias = -0.0012;
  sun.shadow.normalBias = 0.02;
  lights.add(sun, sun.target);
  lights.add(new THREE.HemisphereLight(0xf4f1ea, 0x8e887f, 0.22));
}

function render(c, w, h) {
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setSize(w, h, false);
  camera.fov = 2 * Math.atan(1 / c.fy) * 180 / Math.PI;
  camera.aspect = w / h;
  // 自前のエンジンは up にピッチ込みのベクトルを持つが、lookAt には鉛直を渡す。
  camera.up.set(0, 1, 0);
  camera.position.set(c.eye[0], c.eye[1], c.eye[2]);
  camera.lookAt(c.eye[0] + c.forward[0], c.eye[1] + c.forward[1], c.eye[2] + c.forward[2]);
  camera.updateProjectionMatrix();
  renderer.render(scene, camera);
}

window.clinicHQ = { init, build, render,
  bounds(){const b=new THREE.Box3().setFromObject(group);return [b.min.toArray(),b.max.toArray()];} };
window.dispatchEvent(new Event('clinic-hq-ready'));
