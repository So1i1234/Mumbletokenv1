$ErrorActionPreference = 'Stop'
$python = 'C:\Users\mrsro\AppData\Local\Programs\Python\Python313\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Python 3.10+ was not found. Update the Python path in this script or install Python and PyInstaller.' }
Push-Location $PSScriptRoot
try {
    & $python -m PyInstaller --noconfirm --clean --onefile --windowed --name mumbledtoken --distpath (Join-Path $PSScriptRoot 'mumbledtoken_dist') --workpath (Join-Path $PSScriptRoot 'mumbledtoken_build') --specpath (Join-Path $PSScriptRoot 'mumbledtoken_spec') (Join-Path $PSScriptRoot 'mumbledtoken_app.py')
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed to build mumbledtoken.exe.' }
    Copy-Item (Join-Path $PSScriptRoot 'mumbledtoken_dictionary.json') (Join-Path $PSScriptRoot 'mumbledtoken_dist\mumbledtoken_dictionary.json') -Force
    Write-Host "Built $(Join-Path $PSScriptRoot 'mumbledtoken_dist\mumbledtoken.exe')"
} finally { Pop-Location }
