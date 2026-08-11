$ErrorActionPreference = 'Stop'

$outDir = 'F:\sun\sunhan\my_test\paper2_sci\18_manuscript_v1'
$word = $null
try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    foreach ($stem in @('manuscript_v1_en', 'manuscript_v1_zh')) {
        $docx = Join-Path $outDir ($stem + '.docx')
        $pdf = Join-Path $outDir ($stem + '.pdf')
        $doc = $word.Documents.Open($docx, $false, $true)
        try {
            $doc.Fields.Update() | Out-Null
            $doc.ExportAsFixedFormat($pdf, 17)
        }
        finally {
            $doc.Close($false)
        }
    }
}
finally {
    if ($null -ne $word) {
        $word.Quit()
        [System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($word) | Out-Null
    }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}

Get-Item -LiteralPath (Join-Path $outDir 'manuscript_v1_en.pdf'), (Join-Path $outDir 'manuscript_v1_zh.pdf') | Select-Object Name, Length
