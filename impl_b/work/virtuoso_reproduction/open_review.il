load("/home/EDA/mentor/calibre2026/aok_cal_2026.1_17.11/lib/calibre.skl")
drLoadDrf("/mnt/c/EDA_Codex/Lab06b/work/virtuoso_reproduction/out/report_colors.drf" nil)
labCV=dbOpenCellViewByType("lab06b_crosscad_20261031" "lab06b_b7_ec_pad_chip" "layout" "" "r")
unless(labCV error("Run native import_crosscad.sh in the canonical C project first."))
tf=techGetTechFile(ddGetObj("lab06b_crosscad_20261031"))
foreach(pair list(list("L3" "rptBlue" "blank") list("L41" "rptGreen" "solid") list("L39" "rptOrange" "solid") list("L4" "rptYellow" "solid") list("L5" "rptPink" "solid") list("L99" "rptBrown" "blank") list("L100" "rptLabel" "solid") list("L1002" "rptLabel" "blank"))
 lp=techGetLP(tf list(car(pair) "drawing"))
 when(lp drSetPacket("display" techGetLPPacketName(lp) caddr(pair) "solid" cadr(pair) cadr(pair) if(equal(caddr(pair) "blank") then "outline" else "solid"))))
hiRegTimer("when(boundp('lxiDialogBox) hiDBoxOK(lxiDialogBox))" 20)
envSetVal("layout" "displayResolution" 'string "Very High")
deOpenCellView("lab06b_crosscad_20261031" "lab06b_b7_ec_pad_chip" "layout" "maskLayout" nil "r")
procedure(labReviewFit()
 foreach(win hiGetWindowList()
  when(errset(geGetWindowCellView(win) nil) && geGetWindowCellView(win)==labCV
   win~>displayResolution="Very High"
   win~>stopLevel=32
   hiResizeWindow(win list(0:0 1800:1000))
   hiZoomIn(win list(-1040:-1000 3060:840)))))
hiRegTimer("labReviewFit()" 35)
