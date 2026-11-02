; 讀 Virtuoso OA library，統計 cell、instance、各層圖形數與多邊形最大點數，找出頂層 cell。
; 由 virtuoso.sh 以 virtuoso -nograph -replay 執行；輸出檔名取自環境變數 OA_REPORT。
let((lib names refd nInst nShape maxPts out cv top)
  lib = ddGetObj("B7_CHIP")
  names = lib~>cells~>name
  refd = makeTable("refd" nil)
  nShape = makeTable("nShape" 0)
  maxPts = makeTable("maxPts" 0)
  nInst = 0
  foreach(n names
    cv = dbOpenCellViewByType("B7_CHIP" n "layout" nil "r")
    when(cv
      foreach(i cv~>instances
        refd[i~>cellName] = t
        nInst = nInst + 1)
      foreach(s cv~>shapes
        let((k)
          k = sprintf(nil "%s/%s/%s" s~>layerName s~>purpose s~>objType)
          nShape[k] = nShape[k] + 1
          when(s~>objType == "polygon"
            maxPts[k] = max(maxPts[k] s~>nPoints))))
      dbClose(cv)))
  out = outfile(getShellEnvVar("OA_REPORT"))
  fprintf(out "cells %d\n" length(names))
  fprintf(out "instances %d\n" nInst)
  foreach(n names unless(refd[n] fprintf(out "top %s\n" n)))
  foreach(k nShape fprintf(out "shapes %s %d %d\n" k nShape[k] maxPts[k]))
  top = car(setof(n names !refd[n]))
  cv = dbOpenCellViewByType("B7_CHIP" top "layout" nil "r")
  fprintf(out "bbox %L\n" cv~>bBox)
  fprintf(out "dbu %L\n" cv~>DBUPerUU)
  dbClose(cv)
  close(out))
exit()
