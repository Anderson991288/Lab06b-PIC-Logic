.left.controlf.rules invoke
.right.content.rules_frame.runfrm.runf.rundir delete 0 end
.right.content.rules_frame.runfrm.runf.rundir insert 0 /mnt/c/EDA_Codex/Lab06b/work/virtuoso_reproduction/out/gui_auto
.left.controlf.inputs invoke
set base .right.content.inputs_frame.tabs.layout
foreach {w value} [list $base.lpfrm.textf lab06b_b7_ec_pad_chip.calibre.db $base.pcfrm.entry lab06b_b7_ec_pad_chip] {$w delete 0 end;$w insert 0 $value}
set check $base.ipfrm.fromviewer
if {![set [$check cget -variable]]} {$check invoke}
after 0 {cmn::save_runset . 1}
