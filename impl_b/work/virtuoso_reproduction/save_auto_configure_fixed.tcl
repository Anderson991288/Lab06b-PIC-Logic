.getSaveFileNameDlg1.top.vc.entry delete 0 end
.getSaveFileNameDlg1.top.vc.entry insert 0 /mnt/c/EDA_Codex/Lab06b/work/virtuoso_reproduction/out/GUI_auto_saved.runset
.getSaveFileNameDlg1.buttons.action invoke
.left.controlf.rules invoke
.right.content.rules_frame.runfrm.runf.rundir delete 0 end
.right.content.rules_frame.runfrm.runf.rundir insert 0 /mnt/c/EDA_Codex/Lab06b/work/virtuoso_reproduction/out/gui_fixed
.left.controlf.inputs invoke
set base .right.content.inputs_frame.tabs.layout
set check $base.ipfrm.fromviewer
if {[set [$check cget -variable]]} {$check invoke}
foreach {w value} [list $base.lpfrm.textf /mnt/c/EDA_Codex/Lab06b/work/virtuoso_reproduction/out/exports_final/B7_crosscad_final.gds $base.pcfrm.entry LAB06B_B7_EC_PAD_CHIP] {
 $w delete 0 end
 $w insert 0 $value
}
puts "LAB_GUI_FIXED_CONFIG EXPORT=[set [$check cget -variable]] FILE=[$base.lpfrm.textf get] TOP=[$base.pcfrm.entry get]"
update idletasks
