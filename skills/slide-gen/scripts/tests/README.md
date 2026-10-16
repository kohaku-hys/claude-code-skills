# 5050ツール 回帰テスト

ppt-master の localhost:5050 サーバ（svg_editor / confirm_ui）と複数デッキ対応の回帰テスト。
2026-06-30 の複数デッキ修正＋監査修正の検証用。**python だけで動く**（node 不要）。

実行（どれも単体で `python <file>`、終了コード0=合格、サーバは自分で起動・停止し後始末する）:

```
python test_multideck.py        # 2デッキが別ポート(5050/5051)に分離・cross-talkなし   10件
python test_confirm_coexist.py  # 5050占有中にconfirm起動→クラッシュせず5051へ          6件
python test_backend_extra.py    # save-all原子性・状態クリア・shutdown身元クロスキル防止  9件
```

一時プロジェクトは `%USERPROFILE%\_slidegen_work\_audit_test\` 配下に作って消す。
コンソールが cp932 の場合は `set PYTHONIOENCODING=utf-8` を付けると文字化けしない。

サーバ本体: ppt-master の `skills/ppt-master/scripts/`（svg_editor, confirm_ui, server_common。置き場の例は `C:/dev/ppt-master/skills/ppt-master/scripts/`、環境変数 `PPT_MASTER_SCRIPTS` で変えられる）。
複数デッキ対応などのサーバの修正は作者が ppt-master のローカルのブランチに入れた物で、上流の ppt-master には入っていない。この3本は、ppt-master が無い時と上流の版（修正の印 `force_release_lock` が server_common.py に無い）の時は、何もせず `[SKIP-ALL]` と出して終わる（pytest では skipped）。
変更履歴は `../../references/CHANGELOG_5050.md`（監査の全 findings の一覧は作者の環境にあり、公開版には含まれない）。

## 2026-09-28 追加

```
python test_deck_doctor.py   # 文字の大きさ・量・です/ます・決まり文句・PREP・目次 A0〜A3・brief・中身 C1〜C6・R0・形 F1〜F8・引用 Q1・Q2・genre G1〜G9  258件
python test_brief.py         # brief.py（証拠の台帳 v2・genre・overview を brief.json と spec_lock へ書く）  27件
python test_claims.py        # claims.py（claims.json の sources_read・roles、照合の記録 evidence_check）  6件
python test_recommend.py     # recommend.py が tier を付けず tier-1 推奨を入れるか  15件
```

件数は 2026-09-28 に数えた実物（deck_doctor・brief・claims は 3.12＝`%LOCALAPPDATA%\Programs\Python\Python312\python.exe` と `py -3`＝3.14 の両方で全件通過。test_recommend は 3.14 で確認）。deck_doctor.py（と build.py）は、作者が ppt-master のローカルのブランチに足した物を slide-gen の `scripts/` に同梱した。test_deck_doctor・test_brief・test_claims は同梱版（`../deck_doctor.py`）を試すので、ppt-master が無くても動く。サーバの試験3本だけが環境変数 `PPT_MASTER_SCRIPTS`（既定は作者の置き場の例 `C:\dev\ppt-master\skills\ppt-master\scripts`）を見る。
test_deck_doctor.py の「試験集」の段と「抽象の語の一覧を文章の検査器と照らす」1件は、作者の環境の文章用スキル（このリポジトリに含まれない）の試験集と検査器を読む。無ければ `[SKIP]` と出して飛ばす。

話す型の検査は delivery を書かなくても動く（配布用は `delivery: document`）。本人指摘「文字が小さい・AIくさい・シンプルじゃない」「PREPを用いるように」「初めに詳細をセレクト方式で決める」「最初に目次を入れたい」への対応。

**test_motion.py**（2026-10-13〜）：motion.py の試験 28件。`py -3 test_motion.py`（python-pptx だけで動く。PowerPoint を使う verify は流さない）。

## pytest でまとめて流す（2026-10-16〜）

`py -m pytest slide-gen/scripts/tests -q`。どのファイルも単体のスクリプトなので、`conftest.py` が1ファイル＝1件として子プロセスで流し、exit 0 を合格にする（試験の中身は変えない）。
