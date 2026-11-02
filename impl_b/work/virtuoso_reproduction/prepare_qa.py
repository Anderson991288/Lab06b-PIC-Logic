from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
code=(ROOT/'work/single_report/check_browser.cjs').read_text(encoding='utf-8')
code=code.replace('structure.articles!==19','structure.articles!==20').replace('All 19 embedded','All 20 embedded').replace('evidence/single_report_browser.json','evidence/virtuoso_report_browser.json')
code=code.replace("['m1-s2','m2-s6','m3-s2']","['m1-s2','m2-s6','m3-s2','cad-reproduction']")
code=code.replace("const inventory=JSON.parse", "await report.locator('#cad-reproduction-interactive').evaluate(e=>e.scrollIntoView({block:'start'}));await report.screenshot({path:'out/report-cad-interactive.png'});\nconst inventory=JSON.parse")
code=code.replace("await report.screenshot({path:'out/report-mobile-chapter.png'});","await report.screenshot({path:'out/report-mobile-chapter.png'});await report.locator('#cad-reproduction-fracture').evaluate(e=>e.scrollIntoView({block:'start'}));await report.screenshot({path:'out/report-mobile-cad.png'});if(await report.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1))errors.push('mobile CAD chapter overflow');")
(HERE/'check_browser.cjs').write_text(code,encoding='utf-8')
print('Prepared full 20-section interaction parity and display QA')
