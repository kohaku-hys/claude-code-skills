# デッキを作り終えたらサーバを閉じてポートを解放する。
# live preview (svg_editor) と confirm_ui の両方を停止する（どちらも動いていなければ何もしない＝冪等）。
# 各サーバの --shutdown は graceful 停止 → 死んだ pid のロックも掃除する。
# usage: .\stop.ps1 -Project <project_dir>
param([Parameter(Mandatory=$true)][string]$Project)
$SK = "C:\dev\ppt-master\skills\ppt-master\scripts"

Write-Output "閉じています: $Project"
& python "$SK\svg_editor\server.py" "$Project" --shutdown
& python "$SK\confirm_ui\server.py" "$Project" --shutdown
Write-Output "完了（ポート解放）。"
