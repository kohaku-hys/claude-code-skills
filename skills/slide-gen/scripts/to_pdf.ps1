# PDF化: pptx をレンダリング(COM PNG) → Pillow で1つのPDFに結合。
# Word COM のPDFは環境によってハングする（裏に残った WINWORD.EXE）のでこの方式。
# usage: .\to_pdf.ps1 -Pptx <path.pptx> -OutPdf <out.pdf>
param([Parameter(Mandatory=$true)][string]$Pptx, [Parameter(Mandatory=$true)][string]$OutPdf)
$dir = (& "$PSScriptRoot\render_png.ps1" -Pptx $Pptx | Select-Object -Last 1)
& python "$PSScriptRoot\make_pdf.py" $dir $OutPdf
