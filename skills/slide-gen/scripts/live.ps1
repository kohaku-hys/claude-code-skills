# ライブ編集: svg_editor を --live で起動してブラウザで開く（Executor段階のライブプレビュー）。
# ユーザーが要素をクリック→注釈→Apply → svg に data-edit-annotation が保存される。
# 反映は: python $SK/check_annotations.py <project> で読み取り → SVG修正 → 再ビルド。
# 5050 が埋まっていればサーバは自動で次の空きポートへ前進する。実際に bind した
# ポートは <project>/live_preview/lock.json に書かれるので、それを読んで案内する
# （複数デッキを同時に開いても保存先がズレない）。
# usage: .\live.ps1 -Project <project_dir> [-Port 5050]
param([Parameter(Mandatory=$true)][string]$Project, [int]$Port = 5050)
$SK = "C:\dev\ppt-master\skills\ppt-master\scripts"
$server = Join-Path $SK "svg_editor\server.py"
$lock = Join-Path $Project "live_preview\lock.json"

$start = Get-Date
# --no-browser: 外部ブラウザを勝手に開かせない（VSCode の Simple Browser で開く既定に合わせる）。
Start-Process -FilePath "python" -ArgumentList @("`"$server`"", "`"$Project`"", "--port", "$Port", "--live", "--no-browser") -WindowStyle Minimized

# 起動後に書かれた lock.json から実ポートを拾う（最大 ~12 秒待つ）。
# 古い残骸ロックを誤読しないよう、今回の起動より後に更新されたものだけ採用する。
$realPort = $null
for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Milliseconds 200
    if (Test-Path $lock) {
        try {
            $item = Get-Item $lock -ErrorAction Stop
            if ($item.LastWriteTime -ge $start.AddSeconds(-2)) {
                $info = Get-Content $lock -Raw -ErrorAction Stop | ConvertFrom-Json
                if ($info.port) { $realPort = [int]$info.port; break }
            }
        } catch {}
    }
}
if (-not $realPort) { $realPort = $Port }
$url = "http://localhost:$realPort"

try { Set-Clipboard $url } catch {}
Write-Output "svg_editor (live) -> $url  (URLをクリップボードにコピー済み)"
if ($realPort -ne $Port) {
    Write-Output "  ※ポート $Port は使用中だったため $realPort で起動しました（複数デッキ同時OK）"
}
Write-Output "VSCodeで開く: Ctrl+Shift+P -> 'Simple Browser: Show' -> 貼り付け（Ctrl+Alt+B は5050固定なので2つ目以降はこちら）"
Write-Output "注釈反映: python `"$SK\check_annotations.py`" `"$Project`""
Write-Output "作り終わったら閉じる(ポート解放): powershell -File `"$PSScriptRoot\stop.ps1`" -Project `"$Project`""
