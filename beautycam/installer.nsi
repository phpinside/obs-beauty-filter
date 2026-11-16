; BeautyCam 安装程序（NSIS 3.x）
; 编译：makensis installer.nsi  ->  BeautyCam-Setup-1.0.0.exe
; 需要先执行 python build.py，保证 dist\BeautyCam 存在

!define APPNAME "BeautyCam"
!define APPDISPLAY "BeautyCam 美颜摄像头"
!define VERSION "1.0.0"
!define PUBLISHER "BeautyCam"

Name "${APPDISPLAY}"
OutFile "BeautyCam-Setup-${VERSION}.exe"
InstallDir "$LOCALAPPDATA\Programs\BeautyCam"
InstallDirRegKey HKCU "Software\BeautyCam" "InstallDir"
RequestExecutionLevel user
Unicode true
SetCompressor /SOLID lzma

!include "MUI2.nsh"
!define MUI_ABORTWARNING
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "SimpChinese"
!insertmacro MUI_LANGUAGE "English"

Section "主程序" SecMain
  SetOutPath "$INSTDIR"
  File /r "dist\BeautyCam\*.*"
  WriteUninstaller "$INSTDIR\uninstall.exe"

  CreateDirectory "$SMPROGRAMS\BeautyCam"
  CreateShortcut "$SMPROGRAMS\BeautyCam\${APPDISPLAY}.lnk" "$INSTDIR\BeautyCam.exe"
  CreateShortcut "$DESKTOP\${APPDISPLAY}.lnk" "$INSTDIR\BeautyCam.exe"

  WriteRegStr HKCU "Software\BeautyCam" "InstallDir" "$INSTDIR"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\BeautyCam" "DisplayName" "${APPDISPLAY}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\BeautyCam" "DisplayIcon" "$INSTDIR\BeautyCam.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\BeautyCam" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\BeautyCam" "Publisher" "${PUBLISHER}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\BeautyCam" "DisplayVersion" "${VERSION}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\BeautyCam" "UninstallString" '"$INSTDIR\uninstall.exe"'
SectionEnd

Section "Uninstall"
  Delete "$DESKTOP\${APPDISPLAY}.lnk"
  Delete "$SMPROGRAMS\BeautyCam\${APPDISPLAY}.lnk"
  RMDir "$SMPROGRAMS\BeautyCam"
  RMDir /r "$INSTDIR"
  DeleteRegKey HKCU "Software\BeautyCam"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\BeautyCam"
  ; 保留用户配置，如需一并清除可取消下一行注释
  ; RMDir /r "$APPDATA\BeautyCam"
SectionEnd
