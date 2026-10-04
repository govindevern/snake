# Install and use Snake on Windows

## System requirements

The standalone release targets Windows 10 or Windows 11 on x64. End users need no Python installation, package manager, internet connection after downloading the installer, or project source tree.

## Install Snake

1. Download `Snake-Setup-1.1.0.exe` from the release location supplied by the distributor.
2. Run the installer and choose a system-wide installation or, if offered, a per-user installation.
3. Optionally enable the Start Menu shortcut.
4. When setup finishes, open a **new** PowerShell or Command Prompt window so it receives the updated PATH.
5. Confirm installation:

   ```powershell
   snake --version
   snake --help
   ```

The installer stores Snake's program files in its installation directory. It adds only that directory to the applicable user or system PATH, does not replace PATH, and removes only Snake's entry when uninstalled. A system-wide installation may ask for administrator approval; a per-user installation should not need elevation.

## Write and run a first program

Open Notepad, type the following, and save it as `hello.snake` (choose **All files** in the Save dialog so Windows does not append `.txt`):

```snake
show "Hello, Snake!"
let name = input("What is your name? ")
show "Nice to meet you, ${name}!"
```

Open PowerShell in the folder containing the file, or change to that folder with `cd`. Then run:

```powershell
snake check .\hello.snake
snake run .\hello.snake
```

`check` reports syntax errors without executing the file. `run` executes the program. You can also supply an absolute path, such as `snake run "C:\Users\Ada\Documents\hello.snake"`, from any current directory.

## Interactive REPL

Start the interactive interpreter from any directory:

```powershell
snake repl
```

The banner identifies the Snake version. Enter Snake statements at the `snake>` prompt. An unfinished block changes the prompt to `...` and continues collecting lines until the grammar is complete:

```snake
to double(value) do
    give value * 2
end
show double(21)
```

Type `:quit` or `:exit` at a fresh prompt to leave. Ctrl+C cancels the current input; it does not run a PowerShell or Command Prompt command. REPL input is Snake syntax only.

## Remove Snake

Use **Settings > Apps > Installed apps** (or **Control Panel > Programs and Features**) and uninstall **Snake Programming Language**. The uninstaller removes Snake's installed files and its own exact PATH entry; it does not remove other PATH entries or user-created `.snake` programs stored elsewhere.

## Troubleshooting

- **`snake` is not recognized:** close and reopen the terminal. If it still fails, verify the Snake installation folder is in the user or system PATH and start a fresh terminal. Do not replace the existing PATH value.
- **A file cannot be opened:** check the spelling, quotes around paths containing spaces, and the `.snake` extension. Run `snake check` with the same path to diagnose source syntax.
- **An error reports a file, line, and column:** edit the indicated location and rerun `snake check` or `snake run`. Errors are intentionally not hidden.
- **A loop reaches the execution limit:** inspect its condition. For a deliberately unbounded run, use `snake run file.snake --limit 0`; this removes the step safeguard.
- **Installer blocked or not trusted:** obtain the installer from its official release source and verify the published SHA-256 checksum. Do not disable antivirus or change Windows security settings.
- **SmartScreen reputation warning:** this project's release artifacts are unsigned unless the release distributor signs them separately. Verify the checksum and source with the distributor; do not disable security features.

For developers building the installer, see [building.md](building.md).
