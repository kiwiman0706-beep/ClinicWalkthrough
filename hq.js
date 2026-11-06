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
const GLOW = '#fffaf0';   // 器具の発光面につけている色。自己発光で描く。

// メーカーのスウォッチ画像。面の色から引き当てる（仕上げは designScheme が色で決めるので、
// 色がそのまま品番の代わりになる）。w,h はその画像が実物で何メートル分かで、
// この値でUVのスケールが決まる。**確証のあるものと、こちらで置いた仮定が混じっている**：
//   実寸が分かっているもの … PWT4290（板1枚 900×150）、メラミン3種（A4 210×297）、
//                              エコカラット（CG用 3636×2424）
//   仮定しているもの     … 床シートは画像幅＝シート幅1820、クロスは画像幅＝巾920。
//                              メーカーページに柄リピートの記載が無いため。
const TEX = {
  '#aeaaa6': ['FS4274.jpg',      1.820, 0.982, 0.80],   // 1F床 待合・WC(P)
  '#d9d2c5': ['FS4276.jpg',      1.820, 0.982, 0.80],   // 1F床 その他
  '#e8e4e0': ['WVP8255.jpg',     0.920, 0.920, 0.94],   // 1F壁・天井
  '#a78972': ['WVP8041.jpg',     0.920, 0.920, 0.90],   // 1F 待合の木目壁
  '#9f999f': ['WVP8069.jpg',     0.920, 0.920, 0.92],   // ①AC
  '#aeb7a2': ['WVP8257.jpg',     0.920, 0.920, 0.92],   // ②AC
  '#cdc9be': ['WVP8256.jpg',     0.920, 0.920, 0.92],   // ③AC
  '#afb1b6': ['WVP8492.jpg',     0.920, 0.920, 0.92],   // ④AC
  '#e0e0df': ['TH6019.jpg',      0.909, 0.060, 0.70],   // 1F巾木
  '#84716c': ['JC-12031K.jpg',   0.210, 0.297, 0.45],   // 1Fカウンター木部
  '#eee1d4': ['LJ-10234KN74.jpg',0.210, 0.297, 0.35],   // 1Fカウンター天板
  '#ded8cf': ['ECP-315_VSR1N.jpg',3.636, 2.424, 0.95],  // 案B 受付背面エコカラット
  '#e6e5e3': ['WVP8473.jpg',     0.920, 0.920, 0.94],   // 2F壁
  '#96785d': ['PWT4290.jpg',     0.900, 0.150, 0.70],   // 2F床 ロイヤルウッド
  '#7a614a': ['DEC8296.jpg',     0.820, 0.210, 0.80],   // 2F腰壁 ハーデック
  '#79583a': ['TJ-2062K.jpg',    0.210, 0.297, 0.45],   // 2Fカウンター
  '#8a6e60': ['TH60415.jpg',     0.909, 0.060, 0.70],   // 2F巾木
};
const loader = new THREE.TextureLoader();
const cache = new Map();
// 読み込みが終わった画像だけを material.map に差す。
// three.js は未読込のテクスチャを黒い1x1で代用するので、先に map を入れてしまうと
// 読み終わるまで面が真っ黒になる（画面は必要なときしか描かないので、数秒そのまま残る）。
// 代わりに読み終わってから差し、そのとき描き直しを促す。
function withTexture(mat, file, anis) {
  const t = cache.get(file);
  if (t) { mat.map = t; mat.color.setRGB(1, 1, 1); return; }
  loader.load('./textures/' + file, tex => {
    tex.colorSpace = THREE.SRGBColorSpace;
    // スウォッチはシームレス加工されていないので、鏡像で繰り返して継ぎ目を目立たなくする。
    tex.wrapS = tex.wrapT = THREE.MirroredRepeatWrapping;
    tex.anisotropy = anis;
    cache.set(file, tex);
    mat.map = tex; mat.color.setRGB(1, 1, 1); mat.needsUpdate = true;
    window.dispatchEvent(new Event('clinic-hq-dirty'));
  }, undefined, () => console.warn('テクスチャを読めません:', file));
}

let renderer, scene, camera, solid, glass, env, group, lights;

function toLinear(hex) {
  return new THREE.Color().setStyle(hex, THREE.SRGBColorSpace);
}

// 面の法線がいちばん寝ている軸を落として、ワールド座標をそのままUVにする。
// 建物は軸に平行なので、これでタイルが現実の寸法どおりに並ぶ。
function boxUV(v0, v1, v2, w, h, out) {
  const ax = v1[0] - v0[0], ay = v1[1] - v0[1], az = v1[2] - v0[2];
  const bx = v2[0] - v0[0], by = v2[1] - v0[1], bz = v2[2] - v0[2];
  const nx = Math.abs(ay * bz - az * by), ny = Math.abs(az * bx - ax * bz),
        nz = Math.abs(ax * by - ay * bx);
  const pick = ny >= nx && ny >= nz ? 1 : (nx >= nz ? 0 : 2);
  for (const p of [v0, v1, v2]) {
    const u = pick === 0 ? p[2] : p[0];
    const t = pick === 1 ? p[2] : p[1];
    out.push(u / w, t / h);
  }
}

// faces -> 非インデックスの BufferGeometry。三角形ごとに法線が立つので、
// computeVertexNormals() がそのままフラットシェーディングになる。
// w,h を渡すと、同時にボックス投影のUVも作る。
function geometry(faces, w, h) {
  const pos = [], col = [], uv = [], c = new THREE.Color();
  for (const f of faces) {
    c.copy(toLinear(f.c));
    for (let i = 1; i < f.v.length - 1; i++) {
      const tri = [f.v[0], f.v[i], f.v[i + 1]];
      for (const p of tri) {
        pos.push(p[0], p[1], p[2]);
        col.push(c.r, c.g, c.b);
      }
      if (w) boxUV(tri[0], tri[1], tri[2], w, h, uv);
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
  if (w) g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  g.computeVertexNormals();
  return g;
}

function init(canvas) {
  // preserveDrawingBuffer は、描いた絵をあとから canvas から取り出せるようにするため
  // （スクリーンショットや画像の書き出し）。わずかに遅くなるが実用上は問題ない。
  renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false,
                                       preserveDrawingBuffer: true });
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 0.80;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;

  scene = new THREE.Scene();
  scene.background = new THREE.Color(0xf1efe8);
  camera = new THREE.PerspectiveCamera(60, 1, 0.05, 120);

  // 室内の相互反射のかわり。これが無いと影の側が真っ黒になる。
  const pmrem = new THREE.PMREMGenerator(renderer);
  env = pmrem.fromScene(new THREE.RoomEnvironment(), 0.04).texture;
  scene.environment = env;
  scene.environmentIntensity = 0.22;

  group = new THREE.Group();
  scene.add(group);
  lights = new THREE.Group();
  scene.add(lights);
  return true;
}

// 色温度 -> 色。器具リストにある 3500K と 5000K だけ使う。
function kelvin(k) {
  return k >= 4500 ? new THREE.Color(0xfff2e4) : new THREE.Color(WARM);
}

// 照明プランから拾ったダウンライト。lamps は [x,y,z,lm,K,配光半角deg] の配列。
// 1階だけで45灯あるが、**全部を同時にシーンへ入れると環境光が効かなくなり、
// スマホでは到底動かない**。そこで灯具は数個のプールで使い回し、描画のたびに
// カメラに近いものだけを割り当てる。見えていない部屋の灯りは画に出ないので、これで足りる。
const POOL = 10;
let lampData = [], pool = [];
function makePool() {
  while (pool.length < POOL) {
    const l = new THREE.SpotLight(0xffffff, 0, 9, 0.6, 0.45, 2);
    l.visible = false;
    pool.push(l);
  }
  // build() は lights を空にするので、作り置きの灯具は毎回入れ直す。
  for (const l of pool) lights.add(l, l.target);
}
// 強さは光束から。スポットライトの単位はカンデラなので lm/立体角 で出し、
// 見た目で合わせた係数をかけている（厳密な測光ではない）。
function updateLamps(eye) {
  if (!lampData.length) { for (const l of pool) l.visible = false; return; }
  const near = lampData
    .map(d => [(d[0] - eye[0]) ** 2 + (d[2] - eye[2]) ** 2, d])
    .sort((a, b) => a[0] - b[0]).slice(0, POOL);
  pool.forEach((l, i) => {
    const hit = near[i];
    if (!hit) { l.visible = false; return; }
    const [x, y, z, lm, K, deg] = hit[1];
    const a = Math.min(Math.max(deg, 10), 80) * Math.PI / 180;
    const solid = 2 * Math.PI * (1 - Math.cos(a));           // 立体角 sr
    l.visible = true;
    l.color.copy(kelvin(K));
    l.intensity = lm / solid * 0.14;
    l.angle = a;
    l.position.set(x, y, z);
    l.target.position.set(x, 0, z);
    l.target.updateMatrixWorld();
  });
}

// 下り天井のスリットに置く光。coves は [x0,z0,x1,z1,y] の配列。
function placeCoves(coves) {
  for (const [x0, z0, x1, z1, y] of coves) {
    const len = Math.hypot(x1 - x0, z1 - z0);
    const n = Math.max(2, Math.min(6, Math.round(len / 1.2)));
    for (let i = 0; i < n; i++) {
      const t = (i + 0.5) / n;
      const l = new THREE.PointLight(WARM, 2.2, 4.0, 2);
      l.position.set(x0 + (x1 - x0) * t, y - 0.12, z0 + (z1 - z0) * t);
      lights.add(l);
    }
  }
}

function build(faces, glassFaces, coves, opts) {
  group.clear();
  lights.clear();

  // スウォッチのある色はテクスチャ付きのメッシュへ、それ以外は頂点色のまま1つに。
  const anis = renderer.capabilities.getMaxAnisotropy();
  const bins = new Map(), plain = [], glow = [];
  for (const f of faces) {
    const key = (f.c || '').toLowerCase();
    if (key === GLOW) glow.push(f);
    else if (TEX[key]) (bins.get(key) || bins.set(key, []).get(key)).push(f);
    else plain.push(f);
  }
  const common = {
    side: THREE.DoubleSide, metalness: 0.0,
    // 既存エンジンは薄い板を壁に密着させて置くので、Zファイティングを抑える。
    polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1,
  };
  for (const [key, fs] of bins) {
    const [file, w, h, rough] = TEX[key];
    // 読み込み中は品番の代表色でベタ塗りしておく（読み終わったら白に戻して画像だけにする）。
    const mat = new THREE.MeshStandardMaterial({
      ...common, roughness: rough, color: toLinear(key),
    });
    withTexture(mat, file, anis);
    const m = new THREE.Mesh(geometry(fs, w, h), mat);
    m.castShadow = m.receiveShadow = true;
    group.add(m);
  }
  solid = new THREE.Mesh(geometry(plain), new THREE.MeshStandardMaterial({
    ...common, vertexColors: true, roughness: 0.82,
  }));
  solid.castShadow = solid.receiveShadow = true;
  group.add(solid);

  // 器具の発光面。下を向いているので上から光が当たらず、ふつうに塗ると暗く沈む。
  // 自己発光にして、点灯している器具として見えるようにする。
  if (glow.length) {
    group.add(new THREE.Mesh(geometry(glow), new THREE.MeshStandardMaterial({
      ...common, color: 0x000000, emissive: 0xfff4e2, emissiveIntensity: 3.2,
    })));
  }

  if (glassFaces.length) {
    glass = new THREE.Mesh(geometry(glassFaces), new THREE.MeshPhysicalMaterial({
      vertexColors: true, roughness: 0.08, metalness: 0,
      transparent: true, opacity: 0.22, transmission: 0.6, side: THREE.DoubleSide,
    }));
    group.add(glass);
  }

  placeCoves(coves);
  lampData = opts.lamps || [];
  makePool();

  // 昼光。ガラス面のある南西から。室内なので強すぎないように。
  const sun = new THREE.DirectionalLight(DAY, 0.40);
  sun.position.set(-6, 7, 16);
  sun.target.position.set(opts.plan[0] / 2, 0, opts.plan[1] / 2);
  sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048);
  const s = sun.shadow.camera;
  s.left = -14; s.right = 14; s.top = 14; s.bottom = -14; s.near = 1; s.far = 40;
  sun.shadow.bias = -0.0012;
  sun.shadow.normalBias = 0.02;
  lights.add(sun, sun.target);
  lights.add(new THREE.HemisphereLight(0xf4f1ea, 0xcac3b7, 0.14));

  // 床からの照り返しのかわり。真上を向いた平行光なので、下を向いた面だけに効く。
  // これが無いと下り天井の裏や棚の下が灰色に沈む（相互反射を計算していないため）。
  const bounce = new THREE.DirectionalLight(0xead9c2, 0.45);
  bounce.position.set(opts.plan[0] / 2, -4, opts.plan[1] / 2);
  bounce.target.position.set(opts.plan[0] / 2, 0, opts.plan[1] / 2);
  lights.add(bounce, bounce.target);
}

function render(c, w, h) {
  updateLamps(c.eye);
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
