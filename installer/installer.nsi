; Installer for the YouTube Downloader VST2 plugin (built with NSIS 3).
;
; Installs "YouTube Downloader.dll" + "YouTube Downloader.exe" into a
; "YouTube Downloader" folder inside the user's VST2 plugins folder, with an
; uninstaller registered in Apps & Features. Running it again on a computer
; that already has the plugin offers Repair or Uninstall.
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
!include "nsDialogs.nsh"
!include "x64.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"
!include "Sections.nsh"

Var InstalledDir    ; plugin folder of an existing install, "" if none
Var Repairing       ; 1 when the user chose Repair
Var RadioRepair
Var RadioUninstall
Var DllCount        ; used while looking for the VST2 folder
Var BestVstDir
Var BestDllCount

; --- Pages -------------------------------------------------------------------

!define MUI_ABORTWARNING

; Shown only when the plugin is already installed.
Page custom MaintenancePage MaintenancePageLeave

!define MUI_PAGE_CUSTOMFUNCTION_PRE SkipWhenRepairing
!define MUI_WELCOMEPAGE_TITLE "Install the ${PRODUCT} plugin"
!define MUI_WELCOMEPAGE_TEXT "This will install the ${PRODUCT} VST2 plugin, which lets you download videos and audio right inside your DAW.$\r$\n$\r$\nPlease close your DAW before continuing.$\r$\n$\r$\nFor personal and educational use only. Please respect copyright and the sites' Terms of Service."
!insertmacro MUI_PAGE_WELCOME

!define MUI_PAGE_CUSTOMFUNCTION_PRE SkipWhenRepairing
!insertmacro MUI_PAGE_COMPONENTS

!define MUI_PAGE_CUSTOMFUNCTION_PRE SkipWhenRepairing
!define MUI_DIRECTORYPAGE_TEXT_TOP "Choose your DAW's VST2 plugins folder. The plugin will be placed in a '${PLUGIN_SUBDIR}' folder inside it.$\r$\n$\r$\nWe've picked the folder where your other VST2 plugins already are. Not sure? Keep it."
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
  ; Repair needs the installer's files, so Apps & Features only offers Uninstall;
  ; running the installer again offers Repair.
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

  ; Existing install?
  StrCpy $InstalledDir ""
  ReadRegStr $0 SHCTX "${UNINST_KEY}" "InstallLocation"
  ${If} $0 != ""
  ${AndIf} ${FileExists} "$0\Uninstall.exe"
    StrCpy $InstalledDir $0
    ; Keep the shortcuts the way they were.
    ${IfNot} ${FileExists} "$SMPROGRAMS\${PRODUCT}.lnk"
      !insertmacro UnselectSection ${SecStartMenu}
    ${EndIf}
    ${If} ${FileExists} "$DESKTOP\${PRODUCT}.lnk"
      !insertmacro SelectSection ${SecDesktop}
    ${EndIf}
  ${EndIf}

  ; Unless a folder was given with /D=..., default to where we installed
  ; last time, then to the folder holding the user's other VST2 plugins.
  ${If} $INSTDIR == "${DEFAULT_VST_DIR}"
    ReadRegStr $0 SHCTX "${UNINST_KEY}" "VSTFolder"
    ${If} $0 != ""
      StrCpy $INSTDIR $0
    ${Else}
      Call DetectVstFolder
    ${EndIf}
  ${EndIf}
FunctionEnd

; Sets $INSTDIR to the VST2 folder the user's DAWs most likely scan:
; the folder registered under HKLM\Software\VST, otherwise whichever of the
; standard VST2 folders already holds the most plugins.
Function DetectVstFolder
  ReadRegStr $0 HKLM "Software\VST" "VSTPluginsPath"
  ${If} $0 != ""
  ${AndIf} ${FileExists} "$0\*.*"
    StrCpy $INSTDIR $0
    Return
  ${EndIf}

  StrCpy $BestVstDir ""
  StrCpy $BestDllCount 0
  ; On a tie the earlier folder wins, so list the modern default first.
  Push "$COMMONFILES64\VST2"
  Call ConsiderVstFolder
  Push "$PROGRAMFILES64\Steinberg\VSTPlugins"
  Call ConsiderVstFolder
  Push "$PROGRAMFILES64\VSTPlugins"
  Call ConsiderVstFolder
  Push "$COMMONFILES64\Steinberg\VST2"
  Call ConsiderVstFolder

  ${If} $BestVstDir != ""
    StrCpy $INSTDIR $BestVstDir
  ${EndIf}
FunctionEnd

Function ConsiderVstFolder
  Exch $0 ; folder to check
  ${If} ${FileExists} "$0\*.*"
    StrCpy $DllCount 0
    ${Locate} "$0" "/L=F /M=*.dll" "CountDll"
    ${If} $DllCount > $BestDllCount
      StrCpy $BestDllCount $DllCount
      StrCpy $BestVstDir $0
    ${EndIf}
  ${EndIf}
  Pop $0
FunctionEnd

Function CountDll
  IntOp $DllCount $DllCount + 1
  Push ""
FunctionEnd

; --- Repair / Uninstall page -------------------------------------------------

Function MaintenancePage
  ${If} $InstalledDir == ""
    Abort ; fresh install: skip this page
  ${EndIf}
  !insertmacro MUI_HEADER_TEXT "${PRODUCT} is already installed" "Choose what you'd like to do."

  nsDialogs::Create 1018
  Pop $0
  ${NSD_CreateLabel} 0 0 100% 36u "The plugin is installed in:$\r$\n$InstalledDir"
  Pop $0

  ${NSD_CreateRadioButton} 0 44u 100% 12u "&Repair"
  Pop $RadioRepair
  ${NSD_OnClick} $RadioRepair UpdateMaintenanceButton
  ${NSD_CreateLabel} 12u 57u -12u 20u "Reinstall the plugin in the same folder. Fixes missing or damaged files and updates it to version ${VERSION}."
  Pop $0

  ${NSD_CreateRadioButton} 0 84u 100% 12u "&Uninstall"
  Pop $RadioUninstall
  ${NSD_OnClick} $RadioUninstall UpdateMaintenanceButton
  ${NSD_CreateLabel} 12u 97u -12u 20u "Remove the plugin and its shortcuts from this computer."
  Pop $0

  ${NSD_Check} $RadioRepair
  Push $RadioRepair ; stands in for the clicked control
  Call UpdateMaintenanceButton
  nsDialogs::Show
FunctionEnd

Function UpdateMaintenanceButton
  Pop $0 ; clicked control (when called from a click)
  GetDlgItem $1 $HWNDPARENT 1
  ${NSD_GetState} $RadioUninstall $0
  ${If} $0 == ${BST_CHECKED}
    SendMessage $1 ${WM_SETTEXT} 0 "STR:&Uninstall"
  ${Else}
    SendMessage $1 ${WM_SETTEXT} 0 "STR:&Repair"
  ${EndIf}
FunctionEnd

Function MaintenancePageLeave
  ${NSD_GetState} $RadioUninstall $0
  ${If} $0 == ${BST_CHECKED}
    ; Work from elsewhere so we don't keep the plugin folder open (it's our
    ; working directory otherwise), then run the installed uninstaller in
    ; place so we can wait for it.
    SetOutPath "$TEMP"
    ClearErrors
    ExecWait '"$InstalledDir\Uninstall.exe" /S _?=$InstalledDir' $1
    ${If} ${Errors}
    ${OrIf} $1 != 0
      MessageBox MB_ICONEXCLAMATION "The plugin is in use, so it couldn't be removed.$\r$\n$\r$\nClose your DAW and try again."
      Abort ; stay on this page
    ${EndIf}
    ; Running in place leaves the uninstaller itself behind. Windows can take
    ; a moment to release it after the process exits, so retry briefly.
    StrCpy $2 0
    ${Do}
      Delete "$InstalledDir\Uninstall.exe"
      RMDir "$InstalledDir"
      ${IfNot} ${FileExists} "$InstalledDir\*.*"
        ${Break}
      ${EndIf}
      Sleep 250
      IntOp $2 $2 + 1
    ${LoopWhile} $2 < 20
    MessageBox MB_ICONINFORMATION "${PRODUCT} has been uninstalled."
    Quit
  ${EndIf}

  ; Repair: reinstall into the same VST2 folder, skipping the other pages.
  StrCpy $Repairing 1
  ReadRegStr $0 SHCTX "${UNINST_KEY}" "VSTFolder"
  ${If} $0 != ""
    StrCpy $INSTDIR $0
  ${EndIf}
FunctionEnd

Function SkipWhenRepairing
  ${If} $Repairing == 1
    Abort
  ${EndIf}
FunctionEnd

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
    SetErrorLevel 2
    Abort
  ${EndIf}
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"

  Delete "$SMPROGRAMS\${PRODUCT}.lnk"
  Delete "$DESKTOP\${PRODUCT}.lnk"
  DeleteRegKey SHCTX "${UNINST_KEY}"
SectionEnd
