# Optional Windows launcher

The launcher starts a separately installed Blender executable with a Baya 3D icon. It does not modify the Blender executable, hide attribution or contain an engine distribution. Its source and artwork are included; compiled executables are excluded from version control.

Build on Windows with the .NET Framework C# compiler:

```powershell
.\branding\build.ps1
```

This regenerates the original icon and builds `branding/Baya 3D.exe`. Copy the built launcher next to `blender.exe` to use it, or keep it within two directory levels beneath the Blender installation. The launcher searches its own directory and up to two parent directories for `blender.exe`.

It opens fullscreen by default. Pass `--windowed` for a maximized normal window; other arguments are forwarded directly to Blender without invoking a shell. Background launches wait for Blender and return its exit code. The optional `--self-test <output.json>` mode reports whether it can find the executable without launching it.

The add-on must be installed separately. Blender remains the engine and keeps its native title/attribution where applicable. Launcher branding is not a standalone Maya-compatible application.
