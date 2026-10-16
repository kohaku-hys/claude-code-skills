# 序盤を決める: confirm_ui（戦略確認UI）を起動してブラウザで開く。
# ここで canvas/mode/visual_style/色/タイポ/icons/images/formula/delivery を確定（八つの確認＝BLOCKING）。
# 確定すると <project>/confirm_ui/result.json が書かれる。それを読んで spec_lock に反映する。
# 5050 が埋まっていればサーバは自動で次の空きポートへ前進する。実際に bind した
# ポートは <project>/.confirm_ui.lock に書かれるので、それを読んで案内する。
# usage: .\confirm.ps1 -Project <project_dir> [-Port 5050]
param([Parameter(Mandatory=$true)][string]$Project, [int]$Port = 5050)
$SK = "C:\dev\ppt-master\skills\ppt-master\scripts"
$server = Join-Path $SK "confirm_ui\server.py"
$lock = Join-Path $Project ".confirm_ui.lock"

$start = Get-Date
# --no-browser: 外部ブラウザを勝手に開かせない（VSCode の Simple Browser で開く既定に合わせる）。
Start-Process -FilePath "python" -ArgumentList @("`"$server`"", "`"$Project`"", "--port", "$Port", "--no-browser") -WindowStyle Minimized

# 起動後に書かれた .confirm_ui.lock から実ポートを拾う（最大 ~12 秒待つ）。
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
Write-Output "confirm_ui -> $url  (URLをクリップボードにコピー済み)"
if ($realPort -ne $Port) {
    Write-Output "  ※ポート $Port は使用中だったため $realPort で起動しました"
}
Write-Output "VSCodeで開く: Ctrl+Shift+P -> 'Simple Browser: Show' -> 貼り付け（Ctrl+Alt+B は5050固定）"
Write-Output "決定後: $Project\confirm_ui\result.json を読んで spec_lock.md に反映"
Write-Output "閉じる(ポート解放): powershell -File `"$PSScriptRoot\stop.ps1`" -Project `"$Project`""
