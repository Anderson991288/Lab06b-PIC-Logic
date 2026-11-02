wm withdraw .
set app calibre-drc:lab06b_classic
if {[lsearch -exact [winfo interps] $app]<0} {error "Current native Calibre interpreter absent"}
if {$argc!=1} {error "Usage script.tcl"}
puts [send $app [list source [lindex $argv 0]]]
exit
