# Host A grid session checklist (PROTOCOL 3.8 background-noise controls, G1 condition 3)

Tick each item before double-clicking `run_grid_hostA.bat`. The script itself checks the ones marked (auto) and refuses to start
if they fail.

- [ ] Restart the laptop first (frees memory: the RAM-fit rule needs file size + 1 GiB available; a DNF counts only after a fresh restart).
- [ ] Charger connected, lid open, laptop on a hard surface (auto: mains).
- [ ] Power mode set to **Best performance** (Settings, System, Power) (recorded automatically with `powercfg`).
- [ ] Windows Update paused (Settings, Windows Update, Pause updates).
- [ ] No Microsoft Defender scan running or scheduled in the next 3 hours.
- [ ] OneDrive and any cloud sync paused.
- [ ] WSL shut down: `wsl --shutdown` in Command Prompt (auto: refuses if WSL is running).
- [ ] The Claude app and all other programs closed (auto: refuses if the Claude app is running).
- [ ] Do not touch the laptop until the window says "Session finished".

After the session: reopen the Claude app and say "grid session done". Claude reads `results/raw/A/` and `results/RUNLOG.md`,
checks every flag, commits and pushes. If cells are left (3-hour limit, DNF, or sentinel re-runs), repeat this checklist for the next
session: the script resumes where it stopped.
