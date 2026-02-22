' Voice Paste - Windowless Launcher
' Bu VBS scripti konsol penceresi acmadan uygulamayi baslatir.
' Taskbar'a pinlemek icin: Sag tikla > Gorev cubuguna sabitle

Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.Run "pythonw voice_paste_gui.py", 0, False
