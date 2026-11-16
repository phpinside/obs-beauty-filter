; obs-beauty-filter 安装包（NSIS 3.x）
; 前提：已运行 build-windows.bat，存在 dist\obs-plugins\64bit\obs-beauty-filter.dll
; 编译：makensis installer.nsi  ->  obs-beauty-filter-Setup-1.0.0.exe

!define PLUGIN "obs-beauty-filter"
!define DISPLAY "OBS 美颜滤镜 (obs-beauty-filter)"
!define VERSION "1.0.0"

Name "${DISPLAY}"
OutFile "obs-beauty-filter-Setup-${VERSION}.exe"
RequestExecutionLevel admin
Unicode true
SetCompressor /SOLID lzma

!include "MUI2.nsh"
!include "LogicLib.nsh"
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "SimpChinese"
!insertmacro MUI_LANGUAGE "English"

; 自动找 OBS：注册表 -> Program Files
Function .onInit
  ReadRegStr $0 HKLM "SOFTWARE\OBS Studio" "InstallPath"
  ${If} $0 != ""
    StrCpy $INSTDIR "$0"
  ${Else}
    StrCpy $INSTDIR "$PROGRAMFILES64\obs-studio"
  ${EndIf}
FunctionEnd

Section "插件" SecPlugin
  ; 目录必须是 OBS 根目录，简单校验一下
  ${IfNot} ${FileExists} "$INSTDIR\bin\64bit\obs64.exe"
    MessageBox MB_ICONSTOP "这个目录不像 OBS 安装目录（找不到 bin\64bit\obs64.exe）。请重新选择。"
    Abort
  ${EndIf}

  SetOutPath "$INSTDIR"
  File /r "dist\obs-plugins"
  File /r "dist\data\obs-plugins"

  WriteRegStr HKLM "Software\${PLUGIN}" "InstallPath" "$INSTDIR"
  WriteUninstaller "$INSTDIR\uninstall-${PLUGIN}.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PLUGIN}" "DisplayName" "${DISPLAY}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PLUGIN}" "DisplayVersion" "${VERSION}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PLUGIN}" "UninstallString" '"$INSTDIR\uninstall-${PLUGIN}.exe"'
SectionEnd

Section "Uninstall"
  Delete "$INSTDIR\obs-plugins\64bit\${PLUGIN}.dll"
  RMDir /r "$INSTDIR\data\obs-plugins\${PLUGIN}"
  Delete "$INSTDIR\uninstall-${PLUGIN}.exe"
  DeleteRegKey HKLM "Software\${PLUGIN}"
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PLUGIN}"
SectionEnd
