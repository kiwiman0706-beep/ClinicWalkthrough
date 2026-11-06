# vendor

`three.min.js` … three.js r187 の `build/three.module.js` と
`examples/jsm/environments/RoomEnvironment.js` を esbuild で1つに束ねて最小化したもの。
高画質ビュー（`hq.js`）だけが使います。既定の描画は従来どおり自前のWebGLで、
このファイルを読み込みません。

作り直すとき：

    npm pack three@0.187.0 && tar xzf three-0.187.0.tgz
    cat > entry.js <<'JS'
    export * from './package/build/three.module.js';
    export { RoomEnvironment } from './package/examples/jsm/environments/RoomEnvironment.js';
    JS
    npx esbuild entry.js --bundle --format=esm --minify --legal-comments=none \
        --outfile=vendor/three.min.js

ライセンスは three.js 本体と同じ MIT（https://github.com/mrdoob/three.js）。
