# find_comment_orphans.ps1
# Finds XML object files referenced ONLY from commented lines (comment orphans)

param(
    [string]$Cabinet = "SHD_03_1"
)

$base = (Resolve-Path "C:\Users\*\Desktop\Modules").Path
$objDir   = Join-Path $base "ventcontent\panels\objects\objects_$Cabinet"
$mnemoDir = Join-Path $base "ventcontent\panels\vision\LCSMnemo\$Cabinet"

if (-not (Test-Path $objDir)) {
    Write-Host "ERROR: $objDir not found" -ForegroundColor Red
    exit 1
}

# 1. Get all XML files in objects dir (relative paths with forward slashes)
$allObjFiles = Get-ChildItem $objDir -Recurse -Filter "*.xml" | ForEach-Object {
    $_.FullName.Substring($objDir.Length + 1).Replace('\', '/')
}

Write-Host "=== Comment Orphan Analysis for [$Cabinet] ===" -ForegroundColor Cyan
Write-Host "Object files: $($allObjFiles.Count)"
Write-Host ""

# 2. Collect ALL search scope files (mnemos + objects XMLs)
$searchFiles = @()
if (Test-Path $mnemoDir) {
    $searchFiles += Get-ChildItem $mnemoDir -Recurse -Filter "*.xml" | Select-Object -ExpandProperty FullName
    Write-Host "Mnemo files in scope: $(($searchFiles | Where-Object { $_ -like "*LCSMnemo*" }).Count)"
}
$searchFiles += Get-ChildItem $objDir -Recurse -Filter "*.xml" | Select-Object -ExpandProperty FullName
Write-Host "Total search scope files: $($searchFiles.Count)"
Write-Host ""

# 3. Build a lookup: for each object file, find all references
$commentOrphans = @()
$activeFiles = @()
$unreferenced = @()
$mixedFiles = @()

$objPrefix = "objects/objects_$Cabinet/"

foreach ($relPath in $allObjFiles) {
    # The reference pattern in XML would be like: objects/objects_SHD_03_1/PV/FPs/heatControl_SHD_03_1.xml
    $searchPattern = [regex]::Escape($relPath)
    
    $activeRefCount = 0
    $commentRefCount = 0
    $activeRefLines = @()
    $commentRefLines = @()
    
    foreach ($searchFile in $searchFiles) {
        # Skip self-references (the file itself)
        $searchRelPath = ""
        if ($searchFile -like "*objects_$Cabinet*") {
            $searchRelPath = $searchFile.Substring($objDir.Length + 1).Replace('\', '/')
            if ($searchRelPath -eq $relPath) { continue }
        }
        
        $lineNum = 0
        $fileName = Split-Path $searchFile -Leaf
        
        foreach ($line in [System.IO.File]::ReadAllLines($searchFile, [System.Text.Encoding]::UTF8)) {
            $lineNum++
            if ($line -match $searchPattern) {
                $trimmed = $line.TrimStart()
                
                # Check if this line is commented:
                # 1. Line starts with //
                # 2. The reference appears after // on the line
                # 3. Line is inside <!-- --> XML comment
                $isCommented = $false
                
                # Check // style comments
                if ($trimmed.StartsWith("//")) {
                    $isCommented = $true
                } else {
                    # Check if // appears before the reference on this line
                    $refIdx = $line.IndexOf($relPath)
                    $commentIdx = $line.IndexOf("//")
                    if ($commentIdx -ge 0 -and $commentIdx -lt $refIdx) {
                        $isCommented = $true
                    }
                    
                    # Check XML comment <!-- -->
                    $xmlCommentStart = $line.IndexOf("<!--")
                    $xmlCommentEnd = $line.IndexOf("-->")
                    if ($xmlCommentStart -ge 0 -and $xmlCommentStart -lt $refIdx) {
                        if ($xmlCommentEnd -lt 0 -or $xmlCommentEnd -gt $refIdx) {
                            $isCommented = $true
                        }
                    }
                }
                
                if ($isCommented) {
                    $commentRefCount++
                    $commentRefLines += "${fileName}:${lineNum}: $($trimmed.Substring(0, [Math]::Min(150, $trimmed.Length)))"
                } else {
                    $activeRefCount++
                    $activeRefLines += "${fileName}:${lineNum}: $($trimmed.Substring(0, [Math]::Min(150, $trimmed.Length)))"
                }
            }
        }
    }
    
    $totalRefs = $activeRefCount + $commentRefCount
    
    if ($totalRefs -eq 0) {
        $unreferenced += $relPath
    } elseif ($activeRefCount -eq 0 -and $commentRefCount -gt 0) {
        $commentOrphans += [PSCustomObject]@{
            File = $relPath
            CommentRefs = $commentRefCount
            Lines = $commentRefLines
        }
    } elseif ($activeRefCount -gt 0 -and $commentRefCount -gt 0) {
        $mixedFiles += [PSCustomObject]@{
            File = $relPath
            ActiveRefs = $activeRefCount
            CommentRefs = $commentRefCount
        }
    } else {
        $activeFiles += $relPath
    }
}

# 4. Report
Write-Host "============================================" -ForegroundColor Yellow
Write-Host "RESULTS for [$Cabinet]:" -ForegroundColor Yellow
Write-Host "============================================" -ForegroundColor Yellow
Write-Host ""
Write-Host "Total object files:           $($allObjFiles.Count)" -ForegroundColor White
Write-Host "Active (non-comment refs):    $($activeFiles.Count)" -ForegroundColor Green
Write-Host "Mixed (active + comment):     $($mixedFiles.Count)" -ForegroundColor DarkYellow
Write-Host "COMMENT ORPHANS (only comment refs): $($commentOrphans.Count)" -ForegroundColor Red
Write-Host "Fully unreferenced:           $($unreferenced.Count)" -ForegroundColor Magenta
Write-Host ""

if ($commentOrphans.Count -gt 0) {
    Write-Host "--- COMMENT ORPHAN FILES ---" -ForegroundColor Red
    foreach ($co in $commentOrphans) {
        Write-Host "  $($co.File)  [comment refs: $($co.CommentRefs)]" -ForegroundColor Red
        foreach ($cl in $co.Lines) {
            Write-Host "      $cl" -ForegroundColor DarkGray
        }
    }
    Write-Host ""
}

if ($mixedFiles.Count -gt 0) {
    Write-Host "--- MIXED FILES (have both active and commented refs) ---" -ForegroundColor DarkYellow
    foreach ($mf in $mixedFiles) {
        Write-Host "  $($mf.File)  [active: $($mf.ActiveRefs), commented: $($mf.CommentRefs)]" -ForegroundColor DarkYellow
    }
    Write-Host ""
}

if ($unreferenced.Count -gt 0) {
    Write-Host "--- FULLY UNREFERENCED ---" -ForegroundColor Magenta
    foreach ($uf in $unreferenced) {
        Write-Host "  $uf" -ForegroundColor Magenta
    }
    Write-Host ""
}

Write-Host "Done." -ForegroundColor Cyan
