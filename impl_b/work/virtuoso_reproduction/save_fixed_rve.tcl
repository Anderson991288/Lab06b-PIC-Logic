set log /mnt/c/EDA_Codex/Lab06b/work/virtuoso_reproduction/out/gui_fixed/interactive_transcript.txt
set fh [open $log w]
puts $fh [.right.content.run_frame.tabs.txtf.pw.transcriptf.txt get 1.0 end]
close $fh
.left.runrvef.startrve invoke
after 0 {cmn::save_runset . 1}
