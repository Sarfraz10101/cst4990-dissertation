# Start the CST4990 guest with host CPU affinity fixed to the eight P-cores.
#
#   powershell -ExecutionPolicy Bypass -File launch_vm_pinned.ps1
#   (or just double-click launch_vm_pinned.bat)
#
# Why this is not simply "set the affinity after starting the VM": VirtualBox's
# hardened loader puts a restrictive DACL on VirtualBoxVM.exe, so assigning
# ProcessorAffinity to it is denied even from an elevated PowerShell. What does
# work, with no elevation at all, is pinning VBoxSVC - the COM server that spawns
# the VM process - because a child inherits its parent's affinity mask.
#
# 0xFFFF = logical CPUs 0-15 = all eight P-cores of the i9-13980HX. The E-cores
# (16-31) are excluded because a thread migrating between core types produces a
# timing step far larger than the side-channel signal being measured. This is a
# methodology control, not a performance tweak - record that you applied it.
#
# Affinity is not persistent. Run this every session, in place of the VirtualBox
# GUI's Start button.

$ErrorActionPreference = "Stop"

$VM       = "Lubuntu-Beginner"
$MASK     = 0xFFFF
$VBoxMgr  = "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"

if (-not (Test-Path $VBoxMgr)) { throw "VBoxManage not found at $VBoxMgr" }

# Touching VirtualBox over its API starts VBoxSVC if it is not already up, so
# there is something to pin before the VM is launched.
& $VBoxMgr list vms | Out-Null

$svc = Get-Process VBoxSVC -ErrorAction SilentlyContinue
if (-not $svc) { throw "VBoxSVC did not start - cannot pin by inheritance" }

$svc.ProcessorAffinity = [IntPtr]$MASK
Write-Host ("VBoxSVC pinned to 0x{0:X} ({1})" -f $MASK, $svc.ProcessorAffinity)

$running = & $VBoxMgr list runningvms
if ($running -match [regex]::Escape($VM)) {
    Write-Warning "$VM is already running - it will NOT be pinned. Shut it down and re-run this script."
} else {
    & $VBoxMgr startvm $VM --type gui
}

# Verify rather than assume. The process with tens of threads is the VM itself;
# the one- and two-thread processes are the hardened loader's stubs.
Write-Host "`nwaiting for the VM process..."
$vmProc = $null
foreach ($i in 1..20) {
    Start-Sleep -Seconds 2
    $vmProc = Get-Process VirtualBoxVM -ErrorAction SilentlyContinue |
              Sort-Object { $_.Threads.Count } -Descending | Select-Object -First 1
    if ($vmProc -and $vmProc.Threads.Count -gt 10) { break }
}

if (-not $vmProc) {
    Write-Warning "No VirtualBoxVM process found. Did the VM fail to start?"
    exit 1
}

$aff = [int64]$vmProc.ProcessorAffinity
Write-Host ("VM pid {0}, {1} threads, affinity {2} (0x{3:X})" -f `
            $vmProc.Id, $vmProc.Threads.Count, $aff, $aff)

if ($aff -eq $MASK) {
    Write-Host "PINNED CORRECTLY - all eight P-cores, no E-cores." -ForegroundColor Green
} else {
    Write-Warning ("Expected {0} (0x{1:X}). The VM did not inherit the mask - " -f $MASK, $MASK) +
                  "treat core migration as an uncontrolled variable and say so in Chapter 3."
    exit 1
}
