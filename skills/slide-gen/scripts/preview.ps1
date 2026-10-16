# プレビュー: pptx をレンダリング → コンタクトシート _all.png を作る（→ Read で一括レビュー）。
# usage: .\preview.ps1 -Pptx <path.pptx> [-Cols 3] [-Open]
param([Parameter(Mandatory=$true)][string]$Pptx, [int]$Cols = 3, [switch]$Open)
$dir = (& "$PSScriptRoot\render_png.ps1" -Pptx $Pptx | Select-Object -Last 1)
$montage = (& python "$PSScriptRoot\montage.py" $dir $Cols | Select-Object -Last 1)
Write-Output $montage
if ($Open) { Start-Process $montage }
