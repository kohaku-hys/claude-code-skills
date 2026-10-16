# confirm_ui（八つの確認）詳細ガイド — slide-gen STEP 序盤の実体

序盤（戦略・体裁）はブラウザの confirm_ui で確定する＝**八つの確認（BLOCKING：ユーザー確定を必ず待つ・勝手に決めない）**。English UI なので、下の日本語ガイドで**推奨込みに提示してから**開く。

## 起動手順（$T = `~/.claude/skills/slide-gen/scripts`）

- **① 事前推奨を流し込む**（localhost を◎付きで開く）：`python "$T\recommend.py" <proj> --profile presentation|report|sns [--pages N]` → `recommendations.json` 生成（icons/images/formula/generation ＋ **色3案・書体3案**を recommend.py の PROFILES の既定で推奨。PROFILES は作者の好みなので、自分の好みに書き換えてよい）。Tier-1（canvas/mode/visual/delivery）は印字された推奨を UI で選ぶ。
- **② 起動**：`& "$T\confirm.ps1" -Project <proj>` → ブラウザの確認UI。**URL（実ポート）はクリップボードにコピーされる**ので必ずそれを開く。5050が空いていれば5050、複数デッキ同時なら自動で5051…と別ポートになる（ランチャーが lock から実ポートを読んで案内）。決定で `<proj>/confirm_ui/result.json` 生成。
- **VSCode内で開く（外部ブラウザでなく・作者の既定）**：`Ctrl+Alt+B` で Simple Browser が**右タブ**に開く（左=コード／右=UI）。ただし**キーバインドは5050固定**。**2つ目以降のデッキ**はポートが5051…になるので、`Ctrl+Shift+P → 'Simple Browser: Show' → クリップボードのURLを貼り付け`で開く。
- **ライブ編集**（Executor段階）：`& "$T\live.ps1" -Project <proj>` → 要素をクリック→注釈→Apply → `python "$SK\check_annotations.py" <proj>` で反映。
- **作り終わったら閉じる（ポート解放・複数デッキ運用の要）**：`& "$T\stop.ps1" -Project <proj>` で live preview と confirm の両サーバを停止しポートを明ける。順に作るときは終わったデッキを stop すると次が5050に戻る（放置サーバ・孤児プロセスを溜めない）。
- 決定後は result.json を読んで **spec_lock.md に転記**（以後ここが唯一の正＝毎ページ再読）。

## 八つの確認 日本語ガイド（◎＝作者の登壇・データ系の既定。自分の好みに合わせて変えてよい）

| 確認 | 選択肢 | 推奨 |
|---|---|---|
| 1. canvas（用紙） | PPT16:9 / PPT4:3 / WeChat / 小红书 / 正方1:1 / 縦9:16 / バナー / A4印刷 | ◎ **PPT16:9（ppt169・1280×720）** |
| 2. mode（論法） | pyramid結論先行 / narrative物語 / instructional教学 / showcase展示 / briefing簡報 | ◎ **pyramid**（イシューからはじめよと整合・全数字に比較） |
| 3. visual_style（体裁18種） | swiss-minimal / data-journalism / editorial / glassmorphism / blueprint / memphis / chalkboard / ink-wash 他 | ◎ データ重視＝**data-journalism**（出典線・微チャート）／すっきり＝swiss-minimal |
| 4. color（配色・AIが3案） | 自由記述（AIが3候補を作る） | ◎ **3色のみ**（ベース＝背景／メイン＝基調文字・面／アクセント＝主役の1色。この3色とその濃淡〔opacity〕だけを使い、4色目の色相は足さない）。**白背景もベースの1色に数える**（白地なら残りはメイン＋アクセントの2色まで／白はノーカウントにしない）。3色を spec_lock に HEX で固定 |
| 5. typography（書体・AIが3案） | 自由記述（AIが3候補） | ◎ 和文 **游ゴシック/Noto Sans JP**＋等幅 Consolas（量産フォント無加工は避ける） |
| 6. icons（アイコン） | tabler-outline / tabler-filled / chunk-filled / phosphor-duotone / emoji / なし | ◎ **tabler-outline**（1デッキ1種） |
| 7. images（画像） | AI生成 / Web来源 / ユーザー提供 / プレースホルダ / なし | ◎ **Web来源（image_search＝CC0/CC）**。AI生成は要キー。非実物は「イメージ」、CC BY系はクレジット |
| 8. delivery（用途・本文px） | text近読20px / balanced商務24px / presentation登壇32px | ◎ 話す型＝**presentation(32px)**／配布＝balanced |

補助：formula（mixed/render-all/**数式無ければtext-only**）、generation_mode（**continuous＝1枚ずつ連続**/split）、image_ai_path（auto/api/host-native/manual）。**英語UIが分かりにくい時は、この表で推奨込みに提示→チャット確定でも可。**
