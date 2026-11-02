; Native Linux Virtuoso SKILL automation. Commands and logs stay on C mount.
load("/home/EDA/mentor/calibre2026/aok_cal_2026.1_17.11/lib/calibre.skl")
labCommandIndex=0
procedure(labPollCommands()
  let((path)
    path=sprintf(nil "/mnt/c/EDA_Codex/Lab06b/work/virtuoso_reproduction/work/commands/%03d.il" labCommandIndex)
    when(isFile(path)
      printf("LAB_COMMAND_START %d\n" labCommandIndex)
      labCommandIndex=labCommandIndex+1
      errset(load(path) t)
      printf("LAB_COMMAND_END %d\n" labCommandIndex-1)
    )
    hiRegTimer("labPollCommands()" 10)
  )
)
hiRegTimer("labPollCommands()" 10)
printf("LAB_NATIVE_SKILL_CONTROL_READY\n")
