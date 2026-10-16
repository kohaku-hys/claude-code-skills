# レンダリング: pptx の各スライドを PowerPoint COM で 1920x1080 PNG に書き出す。
# usage: .\render_png.ps1 -Pptx <path.pptx> [-OutDir <dir>]   → 最終行に出力ディレクトリ
param([Parameter(Mandatory=$true)][string]$Pptx, [string]$OutDir = "")
if (-not $OutDir) { $OutDir = Join-Path ([System.IO.Path]::GetDirectoryName($Pptx)) "_png" }
if (Test-Path $OutDir) { Remove-Item $OutDir -Recurse -Force }
New-Item -ItemType Directory -Path $OutDir | Out-Null
$pp = New-Object -ComObject PowerPoint.Application
$pres = $pp.Presentations.Open($Pptx, $true, $false, $false)
$pres.Export($OutDir, "PNG", 1920, 1080)
$pres.Close(); $pp.Quit()
[System.Runtime.Interopservices.Marshal]::ReleaseComObject($pp) | Out-Null
Write-Output $OutDir
