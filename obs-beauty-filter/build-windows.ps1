param([string]$ObsRoot = 'D:\Program Files\obs-studio')
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
$vs = & $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (!$vs) { throw 'Visual Studio C++ tools missing' }
$cmake = Join-Path $vs 'Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe'
$tool = Get-ChildItem (Join-Path $vs 'VC\Tools\MSVC') -Directory | Sort-Object Name -Descending | Select-Object -First 1
$bin = Join-Path $tool.FullName 'bin\Hostx64\x64'
if (!(Test-Path 'obs\libobs\obs-module.h')) {
  git clone --depth 1 --branch 30.2.3 https://github.com/obsproject/obs-studio.git obs
  if ($LASTEXITCODE) { throw 'OBS headers download failed' }
}
$dll = Join-Path $ObsRoot 'bin\64bit\obs.dll'
if (!(Test-Path $dll)) { throw "Missing $dll" }
New-Item -ItemType Directory -Force build-standalone\sdk | Out-Null
$exports = & "$bin\dumpbin.exe" /exports $dll
if ($LASTEXITCODE) { throw 'Export inspection failed' }
$names = $exports | ForEach-Object { if ($_ -match '^\s+\d+\s+[0-9A-F]+\s+[0-9A-F]+\s+(\S+)') { $Matches[1] } }
@('LIBRARY obs','EXPORTS') + $names | Set-Content build-standalone\obs.def
& "$bin\lib.exe" /def:build-standalone\obs.def /machine:x64 /out:build-standalone\obs.lib
if ($LASTEXITCODE) { throw 'Import library failed' }
$location = $dll.Replace('\','/')
$include = (Join-Path $PSScriptRoot 'obs\libobs').Replace('\','/')
$import = (Join-Path $PSScriptRoot 'build-standalone\obs.lib').Replace('\','/')
@("add_library(OBS::libobs SHARED IMPORTED)","set_target_properties(OBS::libobs PROPERTIES IMPORTED_IMPLIB `"$import`" IMPORTED_LOCATION `"$location`" INTERFACE_INCLUDE_DIRECTORIES `"$include`")") | Set-Content build-standalone\sdk\libobsConfig.cmake
& $cmake -S . -B build-plugin -G 'Visual Studio 17 2022' -A x64 "-Dlibobs_DIR=$PSScriptRoot/build-standalone/sdk"
if ($LASTEXITCODE) { throw 'Configure failed' }
& $cmake --build build-plugin --config RelWithDebInfo
if ($LASTEXITCODE) { throw 'Build failed' }
& $cmake --install build-plugin --config RelWithDebInfo --prefix dist
if ($LASTEXITCODE) { throw 'Install staging failed' }
