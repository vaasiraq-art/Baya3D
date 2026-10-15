param(
    [string]$BlenderExe,
    [switch]$Theme
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot

if (-not $BlenderExe -and $env:BLENDER_EXE) { $BlenderExe = $env:BLENDER_EXE }
if (-not $BlenderExe) {
    $besideRepo = Join-Path (Split-Path -Parent $repoRoot) 'blender.exe'
    if (Test-Path -LiteralPath $besideRepo -PathType Leaf) { $BlenderExe = $besideRepo }
}
if (-not $BlenderExe) {
    $command = Get-Command blender -ErrorAction SilentlyContinue
    if ($command) { $BlenderExe = $command.Source }
}
if (-not $BlenderExe -or -not (Test-Path -LiteralPath $BlenderExe -PathType Leaf)) {
    throw 'Supply -BlenderExe with the path to Blender 5.3, or set BLENDER_EXE.'
}
$BlenderExe = (Resolve-Path -LiteralPath $BlenderExe).Path
$installArguments = @('--background', '--python-exit-code', '1', '--python', (Join-Path $PSScriptRoot 'install.py'))
if ($Theme) { $installArguments += @('--', '--theme') }
& $BlenderExe @installArguments
if ($LASTEXITCODE -ne 0) { throw "Baya 3D installation failed with exit code $LASTEXITCODE." }
