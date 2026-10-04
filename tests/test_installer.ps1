param(
    [Parameter(Mandatory = $true)]
    [string]$Installer,
    [string]$PreviousInstaller,
    [switch]$SystemInstall
)

$ErrorActionPreference = "Stop"
$installerPath = (Resolve-Path -LiteralPath $Installer).Path
$previousPath = $null
if ($PreviousInstaller) {
    $previousPath = (Resolve-Path -LiteralPath $PreviousInstaller).Path
}

if ($SystemInstall -and
    -not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()
        ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "System install tests require an elevated disposable Windows test machine."
}

$testRoot = Join-Path $env:TEMP ("snake-installer-test-" + [guid]::NewGuid().ToString("N"))
$installDir = Join-Path $testRoot "installed"
$uninstaller = Join-Path $installDir "unins000.exe"
$registrySubkey = if ($SystemInstall) {
    "SYSTEM\CurrentControlSet\Control\Session Manager\Environment"
} else {
    "Environment"
}
$registryRoot = if ($SystemInstall) {
    [Microsoft.Win32.Registry]::LocalMachine
} else {
    [Microsoft.Win32.Registry]::CurrentUser
}
$target = if ($SystemInstall) { "/ALLUSERS" } else { "/CURRENTUSER" }
$sentinel = Join-Path $testRoot "unrelated-path-entry"
$originalExists = $false
$originalPath = $null
$originalKind = $null
$installed = $false

function Read-PathValue {
    $key = $registryRoot.OpenSubKey($registrySubkey)
    if ($null -eq $key) {
        return @{ Exists = $false; Value = ""; Kind = [Microsoft.Win32.RegistryValueKind]::ExpandString }
    }
    try {
        $exists = $key.GetValueNames() -contains "Path"
        $value = ""
        $kind = [Microsoft.Win32.RegistryValueKind]::ExpandString
        if ($exists) {
            $value = [string]$key.GetValue(
                "Path", "", [Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames)
            $kind = $key.GetValueKind("Path")
        }
        return @{ Exists = $exists; Value = $value; Kind = $kind }
    } finally {
        $key.Dispose()
    }
}

function Write-PathValue([string]$Value, [Microsoft.Win32.RegistryValueKind]$Kind) {
    $key = $registryRoot.CreateSubKey($registrySubkey)
    try {
        $key.SetValue("Path", $Value, $Kind)
    } finally {
        $key.Dispose()
    }
}

function Invoke-Setup([string]$Path) {
    $arguments = @(
        "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", $target,
        "/DIR=`"$installDir`""
    )
    $process = Start-Process -FilePath $Path -ArgumentList $arguments -Wait -PassThru
    if ($process.ExitCode -ne 0) {
        throw "Setup exited with code $($process.ExitCode): $Path"
    }
}

function Assert-SnakePath([string]$Value, [bool]$Expected) {
    $snakeEntries = @($Value -split ";" | Where-Object {
        $_.TrimEnd("\").Equals($installDir.TrimEnd("\"), [StringComparison]::OrdinalIgnoreCase)
    })
    if ($Expected -and $snakeEntries.Count -ne 1) {
        throw "Expected exactly one Snake PATH entry; found $($snakeEntries.Count)."
    }
    if (-not $Expected -and $snakeEntries.Count -ne 0) {
        throw "Snake PATH entry remains after uninstall."
    }
}

try {
    New-Item -ItemType Directory -Path $sentinel -Force | Out-Null
    $snapshot = Read-PathValue
    $originalExists = $snapshot.Exists
    $originalPath = $snapshot.Value
    $originalKind = $snapshot.Kind
    $seed = if ($originalPath) { "$originalPath;$sentinel" } else { $sentinel }
    Write-PathValue $seed $originalKind

    if ($previousPath) {
        Invoke-Setup $previousPath
        $installed = $true
        if (-not (Test-Path -LiteralPath (Join-Path $installDir "snake.exe"))) {
            throw "Previous setup did not install snake.exe."
        }
    }

    Invoke-Setup $installerPath
    $installed = $true
    if (-not (Test-Path -LiteralPath (Join-Path $installDir "snake.exe"))) {
        throw "Setup did not install snake.exe."
    }
    Assert-SnakePath (Read-PathValue).Value $true

    $installedExe = Join-Path $installDir "snake.exe"
    $versionOutput = & $installedExe --version
    if ($LASTEXITCODE -ne 0 -or $versionOutput -notmatch "^Snake 1\.1\.0$") {
        throw "Installed executable failed its version check: $versionOutput"
    }

    if (-not $previousPath) {
        Invoke-Setup $installerPath
        Assert-SnakePath (Read-PathValue).Value $true
    }

    $env:PATH = (Read-PathValue).Value
    $env:SNAKE_EXPECTED_EXE = $installedExe
    $powershell = Join-Path $env:WINDIR "System32\WindowsPowerShell\v1.0\powershell.exe"
    $resolved = & $powershell -NoProfile -Command `
        "if ((Get-Command snake -ErrorAction Stop).Source -ne `$env:SNAKE_EXPECTED_EXE) { exit 2 }; snake --version"
    if ($LASTEXITCODE -ne 0 -or $resolved -notmatch "Snake 1\.1\.0") {
        throw "A new PATH-based process could not resolve the installed Snake command."
    }

    if (Test-Path -LiteralPath $uninstaller) {
        $uninstallProcess = Start-Process -FilePath $uninstaller `
            -ArgumentList @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART") `
            -Wait -PassThru
        if ($uninstallProcess.ExitCode -ne 0) {
            throw "Uninstaller exited with code $($uninstallProcess.ExitCode)."
        }
        $installed = $false
    } else {
        throw "Could not find the installed uninstaller."
    }

    $afterUninstall = Read-PathValue
    Assert-SnakePath $afterUninstall.Value $false
    if ($afterUninstall.Value -notlike "*$sentinel*") {
        throw "Uninstall removed the unrelated PATH sentinel."
    }
    if (Test-Path -LiteralPath $installDir) {
        throw "Uninstaller left the test installation directory behind."
    }
    Write-Output "Installer, PATH, reinstall/upgrade, executable, and uninstall checks passed."
} finally {
    if ($installed -and (Test-Path -LiteralPath $uninstaller)) {
        try {
            $cleanupProcess = Start-Process -FilePath $uninstaller `
                -ArgumentList @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART") `
                -Wait -PassThru
            if ($cleanupProcess.ExitCode -eq 0) {
                $installed = $false
            } else {
                Write-Warning "Test uninstall failed with code $($cleanupProcess.ExitCode); preserving the test installation."
            }
        } catch {
            Write-Warning "Test uninstall failed; preserving the test installation: $_"
        }
    }
    if ($originalExists) {
        Write-PathValue $originalPath $originalKind
    } else {
        $key = $registryRoot.OpenSubKey($registrySubkey, $true)
        if ($null -ne $key) {
            try {
                $key.DeleteValue("Path", $false)
            } finally {
                $key.Dispose()
            }
        }
    }
    if (-not $installed -and (Test-Path -LiteralPath $testRoot)) {
        Remove-Item -LiteralPath $testRoot -Recurse -Force
    } elseif ($installed) {
        Write-Warning "Preserving test files for manual cleanup: $testRoot"
    }
    Remove-Item Env:SNAKE_EXPECTED_EXE -ErrorAction SilentlyContinue
}
