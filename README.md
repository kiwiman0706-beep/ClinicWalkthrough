# クリニック内装・パース出力（PWA）

クリニックの図面をもとにした 3D ウォークスルーです。室内を歩き回る／3D 俯瞰で見る／
平面図で家具を動かす、壁紙・床・床柄の変更、GLB 書き出しができます。

スマホ・タブレットの **ホーム画面に追加** すると、ブラウザの UI なしの全画面で起動し、
**オフラインでも動きます**（アプリ本体は 1 ファイルで完結していて、外部への通信はありません）。

## 画面の使い方

画面いっぱいがプレビューです。操作はすべて画面上に重ねています。

* **上部のタブ** — 左が階（1F / 2F）、中央が見方（歩く / 俯瞰 / 平面図）、右が内装・出力の設定パネル
* **右下の十字パッド** — Google マップ／Google Earth と同じ操作感です
  * 中央：視点を最初の位置に戻す
  * 上下左右の矢印：歩くモードでは前後・左右に移動、俯瞰では視点を寄せる
  * 左上・右上の回り込み矢印：左右を向く（俯瞰では回転）
  * 左下・右下の山形：視線を上げる／下げる
* **右下の ＋ / −** — 拡大・縮小（画面のピンチ、マウスホイールでも同じ）
* **画面のドラッグ** — 歩くモードは見回す、俯瞰は回転、平面図は家具の移動
* **左上のチップ** — 部屋へ一気に移動、室内の視点プリセット
* **キーボード** — 矢印キー / WASD で歩く

## 公開する（GitHub Pages）

1. GitHub のリポジトリ → **Settings** → **Pages** → *Build and deployment* の
   **Source** を **GitHub Actions** に変更する。
2. `main` ブランチに push する（`.github/workflows/deploy-pages.yml` が自動でデプロイします）。
3. 数分後 `https://kiwiman0706-beep.github.io/clinicwalkthrough/` で開けます。

> PWA として動くには **https**（または `localhost`）が必要です。GitHub Pages は https なので
> そのまま使えます。ファイルをダブルクリックして `file://` で開いた場合は
> Service Worker が登録されず、オフライン機能とインストールは使えません（表示自体は動きます）。

## ホーム画面に追加する

* **iPhone / iPad（Safari）**：共有ボタン → 「ホーム画面に追加」。
  ※ Chrome など Safari 以外のブラウザからは追加できません。
* **Android（Chrome）**：右下に出る「ホーム画面に追加」ボタン、
  またはメニュー → 「アプリをインストール」。
* **PC（Chrome / Edge）**：アドレスバー右側のインストールアイコン。

初回はオンラインで一度開いてください。そのときにアプリ本体がキャッシュされ、
以降は電波がなくても起動します。

## 手元で確認する

```bash
python3 -m http.server 8000
# → http://localhost:8000/ をブラウザで開く
```

## アプリ本体を編集する

**このリポジトリが正（マスター）です。** アプリ本体は `src/clinicwalkthrough.html` を直接編集し、
そのあと次を実行して配信用の `index.html` を作り直します。

```bash
python3 tools/apply-pwa-patch.py src/clinicwalkthrough.html   # index.html を作り直す
```

このスクリプトは、アプリ本体には手を加えずに PWA 化に必要な差分だけを当て直します。

* 同一オリジンの manifest・アイコン・Service Worker を読み込めるよう CSP を差し替え
* manifest / テーマカラー / apple-touch-icon などの head タグを追加
* セーフエリア（ノッチ）対応の余白、タップしやすいボタンサイズ、画面高に追従する 3D ビュー
* Service Worker の登録と「ホーム画面に追加」ボタン

編集後は `sw.js` の `CACHE_VERSION` を上げてください（例 `clinic-walkthrough-v2` → `-v3`）。
インストール済みの端末が古いキャッシュを掴んだままになるのを防げます。

### ChatGPT で作った新しい版が来たとき

**そのまま上書きしないでください。** `src/clinicwalkthrough.html` には図面と照合して直した内容が
入っており、上書きすると全部消えます（[docs/図面照合メモ.md](docs/%E5%9B%B3%E9%9D%A2%E7%85%A7%E5%90%88%E3%83%A1%E3%83%A2.md) 参照）。

1. 新しい HTML を別名（例 `src/clinicwalkthrough.new.html`）で置く
2. 現行版との差分を見て、新機能だけを `src/clinicwalkthrough.html` に取り込む
3. 図面照合メモの修正が生きているか確認する
4. `tools/apply-pwa-patch.py` で `index.html` を作り直す

## ファイル構成

| ファイル | 役割 |
| --- | --- |
| `index.html` | 実際に配信されるアプリ（`src/` から生成） |
| `src/clinicwalkthrough.html` | アプリ本体（**編集するのはこのファイル**） |
| `tools/apply-pwa-patch.py` | 本体から `index.html` を作るスクリプト |
| `docs/図面照合メモ.md` | 設計図と突き合わせて直した内容の記録 |
| `manifest.webmanifest` | アプリ名・アイコン・全画面表示などの設定 |
| `sw.js` | オフライン用の Service Worker |
| `icons/` | ホーム画面アイコン |
| `.github/workflows/deploy-pages.yml` | GitHub Pages への自動デプロイ |

## メモ

* 家具の配置は「配置を保存（JSON）」で書き出し、「配置を読み込む」で復元します。
  自動保存はしないので、編集した配置は保存してから閉じてください。
* 壁高・装置・家具は仮設定です。2F 機械室の床上げは未反映です。
