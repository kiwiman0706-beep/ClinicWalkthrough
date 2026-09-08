# クリニック内装・パース出力（PWA）

クリニックの図面をもとにした 3D ウォークスルーです。室内を歩き回る／3D 俯瞰で見る／
平面図で家具を動かす、壁紙・床・床柄の変更、GLB 書き出しができます。

スマホ・タブレットの **ホーム画面に追加** すると、ブラウザの UI なしの全画面で起動し、
**オフラインでも動きます**（アプリ本体は 1 ファイルで完結していて、外部への通信はありません）。

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

## アプリを新しい版に差し替える

アプリ本体（ChatGPT が生成した 1 枚 HTML）は `src/clinicwalkthrough.html` に置いてあります。
新しい HTML をもらったら、それで上書きして次を実行するだけです。

```bash
python3 tools/apply-pwa-patch.py src/clinicwalkthrough.html   # index.html を作り直す
```

このスクリプトが、アプリ本体には手を加えずに PWA 化に必要な差分だけを当て直します。

* 同一オリジンの manifest・アイコン・Service Worker を読み込めるよう CSP を差し替え
* manifest / テーマカラー / apple-touch-icon などの head タグを追加
* セーフエリア（ノッチ）対応の余白、タップしやすいボタンサイズ、画面高に追従する 3D ビュー
* Service Worker の登録と「ホーム画面に追加」ボタン

差し替え後は `sw.js` の `CACHE_VERSION` を上げてください（例 `clinic-walkthrough-v1` → `-v2`）。
インストール済みの端末が古いキャッシュを掴んだままになるのを防げます。

## ファイル構成

| ファイル | 役割 |
| --- | --- |
| `index.html` | 実際に配信されるアプリ（`src/` から生成） |
| `src/clinicwalkthrough.html` | アプリ本体の元ファイル（PWA 化の差分を当てる前） |
| `tools/apply-pwa-patch.py` | 元ファイルから `index.html` を作るスクリプト |
| `manifest.webmanifest` | アプリ名・アイコン・全画面表示などの設定 |
| `sw.js` | オフライン用の Service Worker |
| `icons/` | ホーム画面アイコン |
| `.github/workflows/deploy-pages.yml` | GitHub Pages への自動デプロイ |

## メモ

* 家具の配置は「配置を保存（JSON）」で書き出し、「配置を読み込む」で復元します。
  自動保存はしないので、編集した配置は保存してから閉じてください。
* 壁高・装置・家具は仮設定です。2F 機械室の床上げは未反映です。
