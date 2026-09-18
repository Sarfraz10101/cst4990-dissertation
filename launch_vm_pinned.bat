@echo off
REM Double-clickable wrapper for launch_vm_pinned.ps1.
REM
REM Starts the CST4990 guest with host CPU affinity fixed to the eight P-cores,
REM by pinning VBoxSVC and letting the VM process inherit the mask. See the .ps1
REM for why setting affinity on VirtualBoxVM.exe directly does not work.
REM
REM -ExecutionPolicy Bypass is needed because Windows blocks unsigned .ps1 files
REM by default. It applies to this one invocation only; nothing is changed
REM system-wide.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch_vm_pinned.ps1"
pause
