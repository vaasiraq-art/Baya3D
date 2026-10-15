$ErrorActionPreference = 'Stop'
$brandingRoot = $PSScriptRoot
& (Join-Path $brandingRoot 'generate_icon.ps1')
$compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if (-not (Test-Path -LiteralPath $compiler)) {
    $compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework\v4.0.30319\csc.exe'
}
if (-not (Test-Path -LiteralPath $compiler)) { throw 'The .NET Framework C# compiler is missing.' }
& $compiler /nologo /target:winexe /platform:anycpu /optimize+ /reference:System.Windows.Forms.dll /win32icon:"$brandingRoot\Baya3D.ico" /out:"$brandingRoot\Baya 3D.exe" "$brandingRoot\Baya3DLauncher.cs"
if ($LASTEXITCODE -ne 0) { throw "The launcher compiler exited with code $LASTEXITCODE." }
Get-Item -LiteralPath (Join-Path $brandingRoot 'Baya 3D.exe') | Select-Object FullName, Length
