if {[winfo exists .msgDlg]} {catch {grab release .msgDlg};wm withdraw .msgDlg}
set base .right.content.inputs_frame.tabs.layout
foreach {w value} [list $base.lpfrm.textf lab06b_b7_ec_pad_chip.calibre.db $base.pcfrm.entry lab06b_b7_ec_pad_chip $base.libViewf.lvlf.libEntry lab06b_crosscad_20261031 $base.libViewf.lvvf.viewEntry layout] {
 $w delete 0 end
 $w insert 0 $value
}
set check $base.ipfrm.fromviewer
puts "VIEWER_CHECK_VAR [$check cget -variable] VALUE=[set [$check cget -variable]]"
if {![set [$check cget -variable]]} {$check invoke}
puts "RULE_CONFIG [.right.content.rules_frame.rffrm.rf.entry get] DIR=[.right.content.rules_frame.runfrm.runf.rundir get]"
puts "RUN_CMD [.left.rundrcf.rundrc cget -command] RVE_CMD [.left.runrvef.startrve cget -command]"
set m [.menubar.file cget -menu]
for {set i 0} {$i<=[$m index end]} {incr i} {
 if {[$m type $i] ne "separator" && [$m type $i] ne "tearoff"} {puts "FILE_MENU $i [$m entrycget $i -label] [$m entrycget $i -command]"}
}
update idletasks
puts "READY_LAYOUT [$base.lpfrm.textf get] TOP=[$base.pcfrm.entry get] EXPORT=[set [$check cget -variable]]"
