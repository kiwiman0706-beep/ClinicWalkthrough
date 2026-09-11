# 図面ウォークスルー キット

建築図面（PDF）から、**その場で歩き回れる 3D の内装検討アプリ**を作るための一式です。
図面を読み取ってアプリに起こす作業は Claude にやらせます。あなたは図面と要望を渡して、
できたものを見て「ここ違う」と言うだけです。

* スマホ・タブレットの**ホーム画面に追加**すると全画面で起動し、**オフラインで動きます**
* 外部への通信は一切ありません。アプリ本体は HTML 1 ファイルで完結しています
* 室内を歩く／3D俯瞰／平面図で家具を動かす、**部屋ごとの壁・床・天井・腰壁**の変更、
  GLB 書き出し（Blender で本レンダリング）

---

## まず動かしてみる

`app/index.html` をブラウザで開くだけです。架空の「みどり内科クリニック」が入っています。

> ホーム画面追加とオフラインを試すには https か localhost が必要です。
> ローカルなら `cd app && python3 -m http.server 8000` → http://localhost:8000

## 自分の図面で作る

1. Claude Code（または Claude デスクトップ）でこのフォルダを開く
2. `PROMPT.md` の **① 初回構築** をコピーして、自分の図面 PDF を添付して送る
3. 出てきたものを見て、違うところを日本語で指摘する（`PROMPT.md` の ②〜⑤）

図面がまだ手元にない、または練習したい場合は `sample/sample-plan-1F.pdf` と
`sample-plan-2F.pdf` を使ってください。このサンプル建物そのものです。

## リポジトリにする場合（任意）

使うだけならリポジトリは要りません。フォルダのまま Claude Code で開けば動きます。
履歴を残したい／スマホから見られるように公開したい場合だけ、次のようにします。

1. **private** のリポジトリを作る（⚠️ public にしないこと。図面は施主・設計者の資産です）
2. **zip を展開した中身**をリポジトリの直下に置く（zip ファイルのまま置かないこと。
   Claude は zip の中を編集できません）
3. 自分の図面 PDF を `plans/` に入れる
4. push する

`.github/workflows/deploy-pages.yml` を同梱してあります。GitHub の
**Settings → Pages → Source** を **GitHub Actions** にしておけば、push のたびに
`app/` が自動で公開されます（private リポジトリでの Pages 公開は有料プランが必要です。
無料プランなら公開されるのはサイトだけで、図面を含むリポジトリ自体は非公開のままにできません
──その場合は Pages を使わず、ローカルで開いてください）。

置いたあとのフォルダはこうなります。

```
あなたのリポジトリ/
  README.md  PROMPT.md  GUIDE.md  LICENSE.txt
  app/       ← ここが公開される
  tools/
  sample/
  plans/     ← 自分の図面 PDF を置く
  .github/workflows/deploy-pages.yml
```

## 中身

| ファイル | 説明 |
| --- | --- |
| `README.md` | これ |
| `PROMPT.md` | **Claude に投げるプロンプト集**（初回構築・修正・仕上げ・公開） |
| `GUIDE.md` | 図面をアプリ座標に落とす手順と、モデルを書くためのヘルパー一覧 |
| `app/index.html` | 実際に開くアプリ（`app/src/` から生成） |
| `app/src/walkthrough.html` | アプリ本体（**編集するのはこのファイル**） |
| `app/manifest.webmanifest`, `app/sw.js`, `app/icons/` | ホーム画面追加とオフライン用 |
| `tools/apply-pwa-patch.py` | 本体から `app/index.html` を作り直すスクリプト |
| `tools/apply-settings.py` | アプリで調整した内装を既定値として取り込むスクリプト |
| `sample/sample-plan-1F.pdf`, `-2F.pdf` | 練習用のサンプル図面（架空） |
| `sample/make-sample-plan.py` | そのサンプル図面を生成したスクリプト |
| `sample/building-sample.js` | サンプル建物の定義（書き替えの見本） |

## 作業のながれ

```
図面PDF ──▶ Claude が読み取り ──▶ app/src/walkthrough.html を書く
                                        │
                          python3 tools/apply-pwa-patch.py app/src/walkthrough.html -o app/index.html
                                        ▼
                                  app/index.html を開く
                                        │
              「ここ違う」と指摘 ◀───────┤
                                        │
                アプリで色・家具を調整 ──▶「変更点をコピー」→ Claude に貼る
                                        │
                          python3 tools/apply-settings.py state.json
                                        ▼
                                  既定値として固定
```

## 覚えておくと楽なこと

* **`app/src/walkthrough.html` が正**です。`app/index.html` は毎回そこから作り直されます。
  直接 `index.html` を編集しても次のビルドで消えます。
* **一度アプリに起こしたら、そこから先はアプリが正**。図面を読み直させるのではなく、
  「待合の椅子が反対向き」のように**アプリの表示に対して**指摘するほうが早く正確です。
* 図面に**手書きで丸をつけて撮った写真**を渡すのがいちばん確実です。Claude は読めます。

## 配布について

`LICENSE.txt` を見てください。知人に配るのは自由ですが、**図面そのものは配らないで**ください。
`sample/` の図面は架空のもので、実在の建物ではありません。
