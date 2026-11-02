proc labWalk {w} {
 foreach child [winfo children $w] {
  if {[winfo viewable $child]} {
   set cls [winfo class $child]
   if {[regexp -nocase {button|label|entry|text|menu} $cls]} {
    set txt ""; catch {set txt [$child cget -text]}
    if {$cls eq "Entry"} {catch {set txt [$child get]}}
    puts "WIDGET $child CLASS=$cls TEXT=[string range $txt 0 250]"
   }
   labWalk $child
  }
 }
}
puts "TITLE [wm title .]"
labWalk .
puts "RUNSET_FUNCTIONS [lsearch -all -inline -regexp [info procs] {(?i)(load|open).*runset|runset.*(load|open)|run_drc|rundrc}]"
