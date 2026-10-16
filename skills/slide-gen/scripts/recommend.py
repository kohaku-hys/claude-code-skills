"""recommend.py — confirm_ui の recommendations.json を生成し、localhost が◎付きで開くようにする。
tier-2(realization: icons/images/formula/generation/color3案/typography3案) を下の PROFILES の既定で事前推奨
（PROFILES は作者の好み。自分の好みに書き換えてよい）。
tier-1(canvas/mode/visual_style/delivery) は UI でユーザーが選ぶので推奨値を印字する。
スキーマは実プロジェクトの recommendations.json に準拠。
usage: python recommend.py <project> [--profile presentation|report|sns] [--pages 11] [--notes "..."]
"""
import sys, os, json

PROFILES = {
    "presentation": {  # 作者の既定：登壇・データ系
        "tier1": {"canvas": "ppt169", "mode": "pyramid", "visual_style": "data-journalism", "delivery_purpose": "presentation"},
        "recommend": {"icons": "tabler-outline", "image_usage": ["web"], "formula_policy": "text-only", "generation_mode": "continuous"},
        "body_size": 32},
    "report": {  # 配布レポート
        "tier1": {"canvas": "ppt169", "mode": "briefing", "visual_style": "swiss-minimal", "delivery_purpose": "balanced"},
        "recommend": {"icons": "tabler-outline", "image_usage": ["web"], "formula_policy": "text-only", "generation_mode": "continuous"},
        "body_size": 24},
    "sns": {  # SNS 縦型
        "tier1": {"canvas": "story", "mode": "showcase", "visual_style": "photo-editorial", "delivery_purpose": "presentation"},
        "recommend": {"icons": "tabler-filled", "image_usage": ["web"], "formula_policy": "text-only", "generation_mode": "continuous"},
        "body_size": 32},
}


def palettes():
    return [
        {"name": "青×橙×黒（3色統一・推奨）", "note": "主役=橙、構造=青、本文=黒、背景白＋薄青タイント。データ系で明快。",
         "palette": {"background": "#FFFFFF", "secondary_bg": "#EAF4FB", "primary": "#125E90", "accent": "#E08A2E", "secondary_accent": "#125E90", "body_text": "#14202B"}},
        {"name": "ネイビー×マスタード", "note": "知的・コーポレート。落ち着いた濃紺＋差し色マスタード。",
         "palette": {"background": "#FFFFFF", "secondary_bg": "#EEF1F5", "primary": "#1A365D", "accent": "#E28743", "secondary_accent": "#1A365D", "body_text": "#16202B"}},
        {"name": "深緑×テラコッタ", "note": "自然・落ち着き。モスグリーン＋暖色アクセント。",
         "palette": {"background": "#FFFFFF", "secondary_bg": "#EDF1EE", "primary": "#2F4A3C", "accent": "#C0653B", "secondary_accent": "#2F4A3C", "body_text": "#1B2620"}},
    ]


def typos(sz):
    yg = "'Yu Gothic','Yu Gothic UI',Meiryo,sans-serif"

    def cand(name, note, hcjk, hcss, latin):
        return {"name": name, "note": note,
                "sample_heading": "弱みを、循環で強みに", "sample_heading_latin": "Weakness into strength",
                "sample_body": "具体的な数字と出典で、誰が聞いてもわかるように。", "sample_body_latin": "Plain words, real numbers, sources.",
                "heading": {"cjk": hcjk, "latin": latin, "css": hcss},
                "body": {"cjk": "游ゴシック", "latin": "Arial", "css": yg}, "body_size": sz}
    return [
        cand("游ゴシック（推奨）", "Windows標準で崩れない和文ゴシック。話す型の大見出しに強い。", "游ゴシック", yg, "Arial"),
        cand("明朝見出し（格調）", "見出しを游明朝にして格調。本文はゴシックで可読性確保。", "游明朝", "'Yu Mincho',YuMincho,'MS Mincho',serif", "Georgia"),
        cand("UDゴシック（万人可読）", "BIZ UDPゴシックでUD。誰でも読みやすい。", "BIZ UDPゴシック", "'BIZ UDPGothic',Meiryo,sans-serif", "Arial"),
    ]


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    proj = sys.argv[1]
    prof = sys.argv[sys.argv.index("--profile") + 1] if "--profile" in sys.argv else "presentation"
    pages = sys.argv[sys.argv.index("--pages") + 1] if "--pages" in sys.argv else "11"
    notes = sys.argv[sys.argv.index("--notes") + 1] if "--notes" in sys.argv else ""
    p = PROFILES[prof]
    # 2026-09-28 修正: 以前は "tier": 2 を付け、tier-1 の推奨を印字するだけだった。confirm_ui は tier 2 だと
    # 用紙・聴衆/用途・体裁の欄を描かない（app.js renderForTier）ので、この3つが本人に見えないまま一覧の先頭
    # （swiss-minimal・balanced）で黙って確定していた。tier を付けず（＝全項目を1ページに出す）、
    # tier-1 の推奨も recommend に入れて◎と初期値が正しく付くようにする。
    rec = {
        "lang": "ja",
        "recommend": dict(p["tier1"], **p["recommend"]),
        "page_count": {"value": str(pages)},
        "image_notes": {"value": notes or "本物の現場/対象が一目でわかる現代カラーを優先。非実物は『イメージ』、CC BY系は出典をスライド表示。"},
        "color": {"selected": 0, "candidates": palettes()},
        "typography": {"selected": 0, "candidates": typos(p["body_size"])},
        "refine_spec": {"value": False},
    }
    d = os.path.join(proj, "confirm_ui")
    os.makedirs(d, exist_ok=True)
    out = os.path.join(d, "recommendations.json")
    json.dump(rec, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("wrote " + out)
    t = p["tier1"]
    print("Tier-1 推奨（UIで選ぶ）: canvas=%s / mode=%s / visual_style=%s / delivery=%s"
          % (t["canvas"], t["mode"], t["visual_style"], t["delivery_purpose"]))


if __name__ == "__main__":
    main()
