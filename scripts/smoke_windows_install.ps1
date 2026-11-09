[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$InstallerPath
)

$ErrorActionPreference = "Stop"
$installer = (Resolve-Path -LiteralPath $InstallerPath).Path
$releaseRoot = Split-Path -Parent $installer
$expectedExe = Join-Path $releaseRoot "AJI_TSTAJI_FINAL.exe"
if (-not (Test-Path -LiteralPath $expectedExe)) {
    throw "L'exécutable source du paquet est absent : $expectedExe"
}
$testRoot = Join-Path $env:TEMP "AJI-TSTAJI-installer-smoke-$PID"
$installRoot = Join-Path $testRoot "installed-app"
$profileRoot = Join-Path $testRoot "isolated-localappdata"
$appDataRoot = Join-Path $profileRoot "AJI TSTAJI"
$dataRoot = Join-Path $appDataRoot "data"
$sentinel = Join-Path $dataRoot "persistence-check.txt"

New-Item -ItemType Directory -Path $testRoot | Out-Null
New-Item -ItemType Directory -Path $dataRoot,$installRoot | Out-Null
Set-Content -LiteralPath $sentinel -Value "Keep this test profile" -Encoding ascii

Add-Type @'
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;

public sealed class SmokeWindowInfo {
    public uint ProcessId { get; set; }
    public IntPtr Handle { get; set; }
    public bool Visible { get; set; }
    public string Title { get; set; }
    public string ClassName { get; set; }
}

public static class SmokeWindowProbe {
    private delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
    [DllImport("user32.dll")] private static extern bool EnumWindows(EnumWindowsProc callback, IntPtr lParam);
    [DllImport("user32.dll")] private static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);
    [DllImport("user32.dll")] private static extern bool IsWindowVisible(IntPtr hWnd);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] private static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int count);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] private static extern int GetClassName(IntPtr hWnd, StringBuilder text, int count);
    [DllImport("user32.dll")] private static extern bool PostMessage(IntPtr hWnd, uint message, IntPtr wParam, IntPtr lParam);

    public static List<SmokeWindowInfo> GetWindows(uint[] processIds) {
        var ids = new HashSet<uint>(processIds);
        var windows = new List<SmokeWindowInfo>();
        EnumWindows((hWnd, lParam) => {
            uint processId;
            GetWindowThreadProcessId(hWnd, out processId);
            if (ids.Contains(processId)) {
                var title = new StringBuilder(512);
                var className = new StringBuilder(256);
                GetWindowText(hWnd, title, title.Capacity);
                GetClassName(hWnd, className, className.Capacity);
                windows.Add(new SmokeWindowInfo {
                    ProcessId = processId,
                    Handle = hWnd,
                    Visible = IsWindowVisible(hWnd),
                    Title = title.ToString(),
                    ClassName = className.ToString()
                });
            }
            return true;
        }, IntPtr.Zero);
        return windows;
    }

    public static bool CloseWindow(IntPtr hWnd) {
        return PostMessage(hWnd, 0x0010, IntPtr.Zero, IntPtr.Zero); // WM_CLOSE
    }
}
'@

function Install-TestBuild {
    $arguments = @(
        "/VERYSILENT",
        "/SUPPRESSMSGBOXES",
        "/NORESTART",
        "/DIR=$installRoot"
    )
    $result = Start-Process -FilePath $installer -ArgumentList $arguments -Wait -PassThru
    if ($result.ExitCode -ne 0) {
        throw "L'installateur a échoué (code $($result.ExitCode))."
    }
}

function Assert-TestProfile {
    if (-not (Test-Path -LiteralPath $sentinel)) {
        throw "Le profil de test a été supprimé : $sentinel"
    }
    if ((Get-Content -LiteralPath $sentinel -Raw).Trim() -ne "Keep this test profile") {
        throw "Le contenu du profil de test a été modifié."
    }
}

Install-TestBuild
    $exe = Join-Path $installRoot "AJI_TSTAJI_FINAL.exe"
if (-not (Test-Path -LiteralPath $exe)) {
    throw "L'exécutable installé est absent : $exe"
}
$expectedHash = (Get-FileHash -LiteralPath $expectedExe -Algorithm SHA256).Hash
$installedHash = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash
if ($installedHash -ne $expectedHash) {
    throw "L'exécutable installé ne correspond pas à l'EXE vérifié du paquet."
}
Assert-TestProfile

# Relaunching the same AppId into the same directory simulates an in-place update.
Install-TestBuild
Assert-TestProfile

function Start-And-Close-TestApp {
    $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $exe
    $startInfo.WorkingDirectory = $installRoot
    $startInfo.UseShellExecute = $false
    $startInfo.EnvironmentVariables["LOCALAPPDATA"] = $profileRoot
    $process = [System.Diagnostics.Process]::Start($startInfo)
    try {
        $deadline = (Get-Date).AddSeconds(90)
        $window = $null
        while ((Get-Date) -lt $deadline) {
            $process.Refresh()
            if ($process.HasExited) {
                throw "AJI_TSTAJI_FINAL.exe s'est fermé au démarrage (code $($process.ExitCode))."
            }
            $appProcesses = @(
                Get-Process -Name "AJI_TSTAJI_FINAL" -ErrorAction SilentlyContinue |
                    Where-Object { $_.Path -and [IO.Path]::GetFullPath($_.Path) -ieq [IO.Path]::GetFullPath($exe) }
            )
            $processIds = [uint32[]]@($appProcesses | ForEach-Object { $_.Id })
            $windows = [SmokeWindowProbe]::GetWindows($processIds) |
                Where-Object { $_.Visible }
            $errorWindow = $windows | Where-Object { $_.Title -match "Unhandled exception|Error" } | Select-Object -First 1
            if ($errorWindow) {
                throw "L'application a affiché une fenêtre d'erreur : $($errorWindow.Title)"
            }
            $window = $windows | Where-Object { $_.Title -eq "AJI TSTAJI" } | Select-Object -First 1
            if ($window) {
                break
            }
            Start-Sleep -Seconds 1
        }
        if (-not $window) {
            throw "La fenêtre AJI TSTAJI n'est pas apparue dans les 90 secondes."
        }
    }
    finally {
        $appProcesses = @(
            Get-Process -Name "AJI_TSTAJI_FINAL" -ErrorAction SilentlyContinue |
                Where-Object { $_.Path -and [IO.Path]::GetFullPath($_.Path) -ieq [IO.Path]::GetFullPath($exe) }
        )
        $processIds = [uint32[]]@($appProcesses | ForEach-Object { $_.Id })
        foreach ($appWindow in [SmokeWindowProbe]::GetWindows($processIds) | Where-Object { $_.Title -eq "AJI TSTAJI" }) {
            [SmokeWindowProbe]::CloseWindow($appWindow.Handle) | Out-Null
        }
        if ($process -and -not $process.HasExited) {
            if (-not $process.WaitForExit(10000)) {
                $appProcesses | ForEach-Object { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }
                if (-not $process.HasExited) {
                    $process.Kill()
                }
            }
        }
    }
}

$desktopShortcut = Join-Path ([Environment]::GetFolderPath("Desktop")) "AJI TSTAJI FINAL.lnk"
if (-not (Test-Path -LiteralPath $desktopShortcut)) {
    throw "Le raccourci Bureau AJI TSTAJI FINAL n'a pas été créé."
}
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($desktopShortcut)
if ([IO.Path]::GetFullPath($shortcut.TargetPath) -ne [IO.Path]::GetFullPath($exe)) {
    throw "Le raccourci Bureau ne pointe pas vers l'exécutable installé."
}

Start-And-Close-TestApp
Assert-TestProfile
Start-And-Close-TestApp
Assert-TestProfile

$uninstaller = Get-ChildItem -LiteralPath $installRoot -Filter "unins*.exe" -File |
    Select-Object -First 1
if (-not $uninstaller) {
    throw "Le désinstalleur Inno Setup est absent du dossier de test."
}
$uninstall = Start-Process -FilePath $uninstaller.FullName `
    -ArgumentList @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART") -Wait -PassThru
if ($uninstall.ExitCode -ne 0) {
    throw "La désinstallation de test a échoué (code $($uninstall.ExitCode))."
}
if (Test-Path -LiteralPath $exe) {
    throw "Les fichiers du programme sont encore présents après désinstallation."
}
if (Test-Path -LiteralPath $desktopShortcut) {
    throw "Le raccourci de test n'a pas été retiré pendant la désinstallation."
}
Assert-TestProfile

Write-Host "Installateur vérifié : installation, mise à jour, lancement et désinstallation."
Write-Host "Le profil de test a été conservé dans : $appDataRoot"
