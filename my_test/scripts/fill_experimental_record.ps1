$ErrorActionPreference = 'Stop'

$workspace = 'F:\sun\sunhan'
$templatePath = Join-Path $workspace 'Experimental_Data_Record_Template.docx'
$outputPath = Join-Path $workspace 'Experimental_Data_Record_Filled.docx'
$trialsPath = Join-Path $workspace 'my_test\data\all_trials_135.csv'
$nasaPath = Join-Path $workspace 'my_test\data\nasa_tlx_results\nasa.md'

function Get-ParagraphByText {
    param($Document, [string]$Text)
    foreach ($paragraph in $Document.Paragraphs) {
        $normalized = (([string]$paragraph.Range.Text) -replace '[\r\a\v]', ' ' -replace '\s+', ' ').Trim()
        if ($normalized -eq $Text) { return $paragraph }
    }
    throw "Paragraph not found: $Text"
}

function Remove-ParagraphByText {
    param($Document, [string]$Text)
    $paragraph = Get-ParagraphByText $Document $Text
    $paragraph.Range.Delete()
}

function Remove-ParagraphIfPresent {
    param($Document, [string]$Text)
    foreach ($paragraph in $Document.Paragraphs) {
        $normalized = (([string]$paragraph.Range.Text) -replace '[\r\a\v]', ' ' -replace '\s+', ' ').Trim()
        if ($normalized -eq $Text) {
            $paragraph.Range.Delete()
            return
        }
    }
}

function Add-TableAfterParagraph {
    param($Document, $Paragraph, [object[][]]$Rows, [int[]]$Widths)
    $range = $Document.Range($Paragraph.Range.End, $Paragraph.Range.End)
    $table = $Document.Tables.Add($range, $Rows.Count, $Rows[0].Count)
    $table.AllowAutoFit = $false
    $table.Rows.Item(1).HeadingFormat = -1
    $table.Range.Font.Name = 'Arial'
    $table.Range.Font.NameFarEast = '宋体'
    $table.Range.Font.Size = 8
    for ($row = 1; $row -le $Rows.Count; $row++) {
        for ($column = 1; $column -le $Rows[0].Count; $column++) {
            $cell = $table.Cell($row, $column)
            $cell.Range.Text = [string]$Rows[$row - 1][$column - 1]
            $cell.Range.ParagraphFormat.SpaceAfter = 0
            $cell.Range.ParagraphFormat.Alignment = 1
        }
    }
    for ($column = 1; $column -le $Widths.Count; $column++) {
        $table.Columns.Item($column).Width = $Widths[$column - 1]
    }
    $table.Rows.Item(1).Range.Font.Bold = -1
    return $table
}

$trials = Import-Csv -LiteralPath $trialsPath
if ($trials.Count -ne 135) { throw "Expected 135 trial records; found $($trials.Count)." }

$nasa = Import-Csv -LiteralPath $nasaPath
if ($nasa.Count -ne 45) { throw "Expected 45 NASA-TLX records; found $($nasa.Count)." }

$performanceRows = [System.Collections.Generic.List[object[]]]::new()
$performanceRows.Add([object[]]@('Participant', 'Mode', 'Object', 'Trial', 'Completion Time (s)', 'Success', 'Remark'))
foreach ($trial in ($trials | Sort-Object operator, group_num, object_attr, mode)) {
    $success = if ($trial.outcome -eq 'S') { '1' } else { '0' }
    $performanceRows.Add([object[]]@(
        $trial.operator,
        $trial.mode,
        $trial.specific_object,
        $trial.group_num,
        ('{0:N2}' -f [double]$trial.duration_s),
        $success,
        $trial.object_attr
    ))
}

$nasaRows = [System.Collections.Generic.List[object[]]]::new()
$nasaRows.Add([object[]]@('Participant', 'Mode', 'Object', 'Mental Demand', 'Physical Demand', 'Temporal Demand', 'Performance', 'Effort', 'Frustration', 'Total'))
foreach ($score in ($nasa | Sort-Object operator, object_class, mode)) {
    $total = (([double]$score.mental_demand + [double]$score.physical_demand + [double]$score.temporal_demand + [double]$score.performance + [double]$score.effort + [double]$score.frustration) / 6)
    $nasaRows.Add([object[]]@(
        ('P{0:D2}' -f [int]$score.operator),
        $score.mode,
        $score.object_class,
        $score.mental_demand,
        $score.physical_demand,
        $score.temporal_demand,
        $score.performance,
        $score.effort,
        $score.frustration,
        ('{0:N2}' -f $total)
    ))
}

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
$document = $null
try {
    Copy-Item -LiteralPath $templatePath -Destination $outputPath -Force
    $document = $word.Documents.Open($outputPath)

    # Remove any plain-text placeholders inherited from the template.
    Remove-ParagraphIfPresent $document 'Participant ID | Experience | Date P01 | | P02 | | P03 | |'
    Remove-ParagraphIfPresent $document 'Participant | Mode | Object | Trial | Completion Time(s) | Success | Remark Success: 1=successful grasp, 0=failure'
    Remove-ParagraphIfPresent $document 'Participant | Mode | Object | Mental Demand | Physical Demand | Temporal Demand | Performance | Effort | Frustration | Total'
    Remove-ParagraphIfPresent $document 'Time | Participant | Mode | Object | Event 记录实验开始、结束、成功、失败等事件。'
    for ($index = $document.Tables.Count; $index -ge 1; $index--) { $document.Tables.Item($index).Delete() }

    $participantHeading = Get-ParagraphByText $document 'Participant Information'
    [void](Add-TableAfterParagraph $document $participantHeading @(
        [object[]]@('Participant ID', 'Experience', 'Date'),
        [object[]]@('P01', 'Not recorded', 'Not recorded'),
        [object[]]@('P02', 'Not recorded', 'Not recorded'),
        [object[]]@('P03', 'Not recorded', 'Not recorded')
    ) @(110, 190, 190))

    $performanceHeading = Get-ParagraphByText $document 'Task Performance Record'
    [void](Add-TableAfterParagraph $document $performanceHeading $performanceRows.ToArray() @(57, 35, 82, 35, 80, 40, 55))

    $nasaHeading = Get-ParagraphByText $document 'NASA-TLX Record'
    [void](Add-TableAfterParagraph $document $nasaHeading $nasaRows.ToArray() @(50, 32, 55, 52, 52, 52, 50, 42, 50, 42))

    $rawHeading = Get-ParagraphByText $document 'Raw Experiment Log'
    [void](Add-TableAfterParagraph $document $rawHeading @(
        [object[]]@('Time', 'Participant', 'Mode', 'Object', 'Event'),
        [object[]]@('N/A', 'N/A', 'N/A', 'N/A', 'No timestamped event log was provided with the collected score files.')
    ) @(70, 70, 55, 90, 250))

    $document.Save()
}
finally {
    if ($document -ne $null) { $document.Close($false) }
    if ($word -ne $null) { $word.Quit() }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}

Write-Output "Created: $outputPath"
