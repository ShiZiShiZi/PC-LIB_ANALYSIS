$prodDir = @{}
$testDir = @{}
$sourcePath = "repos\pc-lib-3456\x265_git\source"
Get-ChildItem -Recurse -Path $sourcePath -Include *.cpp,*.h,*.c,*.asm -File | ForEach-Object {
    $isTest = $_.DirectoryName -match "\\test\\" -or $_.DirectoryName -match "\\test$"
    $relPath = $_.DirectoryName.Replace((Resolve-Path $sourcePath).Path + "\", "")
    if (-not $relPath) { $relPath = "." }
    $lines = (Get-Content $_.FullName | Measure-Object -Line).Lines
    if ($isTest) {
        if (-not $testDir.ContainsKey($relPath)) { $testDir[$relPath] = 0 }
        $testDir[$relPath] += $lines
    } else {
        if (-not $prodDir.ContainsKey($relPath)) { $prodDir[$relPath] = 0 }
        $prodDir[$relPath] += $lines
    }
}
Write-Host "=== PRODUCTION ==="
$prodTotal = 0
$prodDir.GetEnumerator() | Sort-Object Value -Descending | ForEach-Object { Write-Host "$($_.Key): $($_.Value)"; $global:prodTotal += $_.Value }
Write-Host "TOTAL PRODUCTION: $prodTotal"
Write-Host "=== TEST ==="
$testTotal = 0
$testDir.GetEnumerator() | Sort-Object Value -Descending | ForEach-Object { Write-Host "$($_.Key): $($_.Value)"; $global:testTotal += $_.Value }
Write-Host "TOTAL TEST: $testTotal"
