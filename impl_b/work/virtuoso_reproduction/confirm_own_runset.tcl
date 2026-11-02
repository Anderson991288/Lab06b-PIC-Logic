if {[.msgDlg.top.msg cget -text] ne "Overwrite file /mnt/c/EDA_Codex/Lab06b/work/virtuoso_reproduction/out/GUI_auto_saved.runset?"} {error "Unexpected dialog"}
.msgDlg.bot.button0 invoke
