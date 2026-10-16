"""
フォームHTMLプレビューを headless Chrome で PNG 化するヘルパ。
日本語(OneDrive)パスでも文字化けしないよう、shell argv ではなく subprocess のリスト渡しで chrome を呼ぶ。
（shell に日本語パスを引数で渡すと化けるが、subprocess の list 引数は Windows で Unicode を正しく渡す）

使い方（呼び出し側は Write ツールで日本語パスを文字列リテラルに埋めた driver を書いて実行する）:
    import sys, os; sys.path.insert(0, os.path.expanduser(r"~/.claude/skills/forms/scripts"))
    from render_preview import render
    render(r"C:\\...OneDrive...\\..._preview.html", r"C:\\...OneDrive...\\..._v1.png", height=3600)
"""
import os, subprocess

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def render(html_path, png_path, height=3600, width=820):
    """html_path をレンダリングして png_path に保存。内容が切れる場合は height を増やす。"""
    url = "file:///" + html_path.replace("\\", "/")
    subprocess.run(
        [CHROME, "--headless=new", "--hide-scrollbars", "--force-device-scale-factor=1",
         "--screenshot=" + png_path, "--window-size=%d,%d" % (width, height), url],
        check=False,
    )
    ok = os.path.exists(png_path)
    print("RENDER=" + ("OK " + png_path if ok else "FAIL"))
    return ok
