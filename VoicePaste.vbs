' Voice Paste - Windowless Launcher
' Bu VBS scripti konsol penceresi acmadan Electron uygulamasini baslatir.
' Taskbar'a pinlemek icin: Sag tikla > Gorev cubuguna sabitle

Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.Run "cmd /c start.bat", 0, False
