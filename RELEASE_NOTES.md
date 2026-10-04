# Snake 1.1.0 release notes

Snake 1.1.0 adds a Windows x64 standalone distribution and offline installer build path while preserving the Snake 1.0 language grammar and tree-walking runtime.

## Highlights

- Bundled `snake.exe` build for users who do not have Python installed.
- CLI startup, file execution, syntax checking, standard-library, and REPL smoke tests with Python removed from PATH.
- Inno Setup source for machine-wide or per-user installation, optional Start Menu shortcut, PATH management, upgrades, and uninstallation.
- REPL version banner and explicit `:quit` / `:exit` commands.
- Release staging with README, license, release notes, standalone archive, and SHA-256 checksums.
- `system.version` now reports the same version as the CLI and distribution metadata.

## Compatibility and limits

- Existing Snake syntax, standard-library interfaces, and `.snake` file execution are retained.
- Windows x64 is the initial prebuilt release target. Build the executable on Windows x64 using 64-bit Python and PyInstaller.
- Inno Setup 6 is an installer-build-time requirement only.
- Installer operation, system-wide PATH modification, upgrade, and uninstall still require validation on a clean Windows 10/11 x64 machine before this release can be certified. Do not treat the installer as tested merely because its source script compiles.
- No code-signing certificate was provided. The generated executable and installer are unsigned; Windows SmartScreen or endpoint protection may display a reputation warning.
