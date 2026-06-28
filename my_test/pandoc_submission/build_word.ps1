$ErrorActionPreference = 'Stop'

$PackageDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $PackageDir
$DataDir = Join-Path $ProjectDir 'data'
$OutputDir = Join-Path $ProjectDir 'output'
$Utf8 = New-Object System.Text.UTF8Encoding($false)
$ManuscriptName = $Utf8.GetString([Convert]::FromBase64String('5Lit5paH5qC45b+D5oqV56i/56i/X+inhuinieivreS5iempseWKqOWkmuWPguaVsOmYu+aKl+i+heWKqemBpeaTjeS9nOaWueazlV/moLzlvI/mlbTnkIbliY3lpIfku70ubWQ='))
$OutputName = $Utf8.GetString([Convert]::FromBase64String('5Yi26YCg5Lia6Ieq5Yqo5YyW5oqV56i/56i/LmRvY3g='))
$Manuscript = Join-Path $DataDir $ManuscriptName
$Reference = Join-Path $PackageDir 'reference.docx'
$Filter = Join-Path $PackageDir 'journal.lua'
$FigureConverter = Join-Path $PackageDir 'convert_figures.py'
$Output = Join-Path $OutputDir $OutputName

foreach ($Path in @($Manuscript, $Reference, $Filter, $FigureConverter)) {
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Missing conversion input: $Path"
    }
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

& python $FigureConverter
if ($LASTEXITCODE -ne 0) {
    throw "Figure preprocessing failed with exit code $LASTEXITCODE"
}

$ResourcePath = "$DataDir;$ProjectDir"
& pandoc `
    --from='markdown+fenced_divs+superscript+pipe_tables+table_captions+tex_math_single_backslash' `
    --to=docx `
    --standalone `
    --reference-doc=$Reference `
    --lua-filter=$Filter `
    --resource-path=$ResourcePath `
    --output=$Output `
    $Manuscript

if ($LASTEXITCODE -ne 0) {
    throw "Pandoc conversion failed with exit code $LASTEXITCODE"
}

Write-Host "Generated: $Output"
