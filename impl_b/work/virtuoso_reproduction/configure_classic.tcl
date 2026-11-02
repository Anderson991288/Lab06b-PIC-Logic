if {[winfo exists .msgDlg.bot.button0]} {.msgDlg.bot.button0 invoke}
wm geometry . 1200x860+300+150
set rule /mnt/c/EDA_Codex/Lab06b/work/virtuoso_reproduction/out/rules/cornerstone_basic_draft.svrf
set run /mnt/c/EDA_Codex/Lab06b/work/virtuoso_reproduction/out/gui_auto
.right.content.rules_frame.rffrm.rf.entry delete 0 end
.right.content.rules_frame.rffrm.rf.entry insert 0 $rule
.right.content.rules_frame.runfrm.runf.rundir delete 0 end
.right.content.rules_frame.runfrm.runf.rundir insert 0 $run
.right.content.rules_frame.rffrm.rf.loadbtn invoke
.left.controlf.inputs invoke
update idletasks
source /mnt/c/EDA_Codex/Lab06b/work/virtuoso_reproduction/remote_inspect.tcl
