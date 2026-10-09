; Installer for the YouTube Downloader VST2 plugin (built with NSIS 3).
;
; Installs "YouTube Downloader.dll" + "YouTube Downloader.exe" into a
; "YouTube Downloader" folder inside the user's VST2 plugins folder, with an
; uninstaller registered in Apps & Features.
;
; Built by build_exe.py:
;   makensis /DDIST_DIR=<folder with the .dll and .exe> /DVERSION=1.0.0 installer.nsi
; Pass /DPER_USER to build a variant that installs without admin rights
; (registry + shortcuts for the current user only) and /DOUTFILE=<path> to
; write it elsewhere - used for testing.

Unicode true
ManifestDPIAware true
SetCompressor /SOLID lzma

!ifndef DIST_DIR
  !error "Pass /DDIST_DIR=<folder containing YouTube Downloader.dll and .exe>"
!endif
!ifndef VERSION
  !define VERSION "1.0.0"
!endif
!ifndef OUTFILE
  !define OUTFILE "${DIST_DIR}\YouTube Downloader VST Setup.exe"
!endif

!define PRODUCT "YouTube Downloader"
!define PLUGIN_SUBDIR "YouTube Downloader"
!define UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\YouTubeDownloaderVST"
!define DEFAULT_VST_DIR "$COMMONFILES64\VST2"

Name "${PRODUCT} VST Plugin"
OutFile "${OUTFILE}"
InstallDir "${DEFAULT_VST_DIR}"
BrandingText "${PRODUCT} ${VERSION}"
AllowSkipFiles off
!ifdef PER_USER
  RequestExecutionLevel user
!else
  RequestExecutionLevel admin
!endif

VIProductVersion "${VERSION}.0"
VIAddVersionKey "ProductName" "${PRODUCT} VST Plugin"
VIAddVersionKey "FileDescription" "${PRODUCT} VST Plugin Setup"
VIAddVersionKey "FileVersion" "${VERSION}"
VIAddVersionKey "ProductVersion" "${VERSION}"
VIAddVersionKey "LegalCopyright" "MIT License"

!include "MUI2.nsh"
!include "x64.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"

; --- Pages -------------------------------------------------------------------

!define MUI_ABORTWARNING

!define MUI_WELCOMEPAGE_TITLE "Install the ${PRODUCT} plugin"
!define MUI_WELCOMEPAGE_TEXT "This will install the ${PRODUCT} VST2 plugin, which lets you download videos and audio right inside your DAW.$\r$\n$\r$\nPlease close your DAW before continuing.$\r$\n$\r$\nFor personal and educational use only. Please respect copyright and the sites' Terms of Service."
!insertmacro MUI_PAGE_WELCOME

!insertmacro MUI_PAGE_COMPONENTS

!define MUI_DIRECTORYPAGE_TEXT_TOP "Choose your DAW's VST2 plugins folder. The plugin will be placed in a '${PLUGIN_SUBDIR}' folder inside it.$\r$\n$\r$\nNot sure? Keep the default - most DAWs scan it automatically."
!define MUI_DIRECTORYPAGE_TEXT_DESTINATION "VST2 plugins folder"
!insertmacro MUI_PAGE_DIRECTORY

!insertmacro MUI_PAGE_INSTFILES

!define MUI_FINISHPAGE_TITLE "The plugin is installed"
!define MUI_FINISHPAGE_TEXT "Installed to:$\r$\n$INSTDIR\${PLUGIN_SUBDIR}$\r$\n$\r$\nNext steps:$\r$\n1. Open your DAW and rescan plugins.$\r$\n2. Add '${PRODUCT}' as an effect on any track.$\r$\n$\r$\nIf your DAW doesn't find it, add the folder above to its VST2 plugin folders in the DAW's settings."
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

; --- Install -----------------------------------------------------------------

Function .onInit
  ${IfNot} ${RunningX64}
    MessageBox MB_ICONSTOP "The ${PRODUCT} plugin requires 64-bit Windows."
    Abort
  ${EndIf}
  SetRegView 64
!ifdef PER_USER
  SetShellVarContext current
!else
  SetShellVarContext all
!endif

  ; Unless a folder was given with /D=..., default to where we installed
  ; last time, then to the system's registered VST2 folder.
  ${If} $INSTDIR == "${DEFAULT_VST_DIR}"
    ReadRegStr $0 SHCTX "${UNINST_KEY}" "VSTFolder"
    ${If} $0 == ""
      ReadRegStr $0 HKLM "Software\VST" "VSTPluginsPath"
    ${EndIf}
    ${If} $0 != ""
      StrCpy $INSTDIR $0
    ${EndIf}
  ${EndIf}
FunctionEnd

Section "VST2 plugin (required)" SecPlugin
  SectionIn RO

  ; If a previous version lives in a different folder, remove it so the DAW
  ; doesn't find two copies.
  ReadRegStr $0 SHCTX "${UNINST_KEY}" "InstallLocation"
  ${If} $0 != ""
  ${AndIf} $0 != "$INSTDIR\${PLUGIN_SUBDIR}"
    Delete "$0\YouTube Downloader.dll"
    Delete "$0\YouTube Downloader.exe"
    Delete "$0\Uninstall.exe"
    RMDir "$0"
  ${EndIf}

  SetOutPath "$INSTDIR\${PLUGIN_SUBDIR}"
  File "${DIST_DIR}\YouTube Downloader.dll"
  File "${DIST_DIR}\YouTube Downloader.exe"
  WriteUninstaller "$INSTDIR\${PLUGIN_SUBDIR}\Uninstall.exe"

  WriteRegStr SHCTX "${UNINST_KEY}" "DisplayName" "${PRODUCT} VST Plugin"
  WriteRegStr SHCTX "${UNINST_KEY}" "DisplayVersion" "${VERSION}"
  WriteRegStr SHCTX "${UNINST_KEY}" "Publisher" "omerfra"
  WriteRegStr SHCTX "${UNINST_KEY}" "DisplayIcon" "$INSTDIR\${PLUGIN_SUBDIR}\YouTube Downloader.exe"
  WriteRegStr SHCTX "${UNINST_KEY}" "InstallLocation" "$INSTDIR\${PLUGIN_SUBDIR}"
  WriteRegStr SHCTX "${UNINST_KEY}" "VSTFolder" "$INSTDIR"
  WriteRegStr SHCTX "${UNINST_KEY}" "UninstallString" '"$INSTDIR\${PLUGIN_SUBDIR}\Uninstall.exe"'
  WriteRegStr SHCTX "${UNINST_KEY}" "QuietUninstallString" '"$INSTDIR\${PLUGIN_SUBDIR}\Uninstall.exe" /S'
  WriteRegDWORD SHCTX "${UNINST_KEY}" "NoModify" 1
  WriteRegDWORD SHCTX "${UNINST_KEY}" "NoRepair" 1
  ${GetSize} "$INSTDIR\${PLUGIN_SUBDIR}" "/S=0K" $0 $1 $2
  WriteRegDWORD SHCTX "${UNINST_KEY}" "EstimatedSize" $0
SectionEnd

Section "Start Menu shortcut (standalone app)" SecStartMenu
  CreateShortcut "$SMPROGRAMS\${PRODUCT}.lnk" "$INSTDIR\${PLUGIN_SUBDIR}\YouTube Downloader.exe"
SectionEnd

Section /o "Desktop shortcut (standalone app)" SecDesktop
  CreateShortcut "$DESKTOP\${PRODUCT}.lnk" "$INSTDIR\${PLUGIN_SUBDIR}\YouTube Downloader.exe"
SectionEnd

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SecPlugin} "The plugin your DAW loads, plus the downloader app it shows."
  !insertmacro MUI_DESCRIPTION_TEXT ${SecStartMenu} "Also open the downloader on its own, outside your DAW, from the Start Menu."
  !insertmacro MUI_DESCRIPTION_TEXT ${SecDesktop} "Also open the downloader on its own from a Desktop shortcut."
!insertmacro MUI_FUNCTION_DESCRIPTION_END

; --- Uninstall ---------------------------------------------------------------

Function un.onInit
  SetRegView 64
!ifdef PER_USER
  SetShellVarContext current
!else
  SetShellVarContext all
!endif
FunctionEnd

Section "Uninstall"
  ClearErrors
  Delete "$INSTDIR\YouTube Downloader.dll"
  Delete "$INSTDIR\YouTube Downloader.exe"
  ${If} ${Errors}
    MessageBox MB_ICONEXCLAMATION "The plugin is in use, so it couldn't be removed.$\r$\n$\r$\nClose your DAW and run the uninstaller again." /SD IDOK
    Abort
  ${EndIf}
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"

  Delete "$SMPROGRAMS\${PRODUCT}.lnk"
  Delete "$DESKTOP\${PRODUCT}.lnk"
  DeleteRegKey SHCTX "${UNINST_KEY}"
SectionEnd
