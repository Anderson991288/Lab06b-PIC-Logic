from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
src=(ROOT/'work/m2_s5/browser_qa.cjs').read_text(encoding='utf-8')
src=src.replace('browser-profile-m2s5','browser-profile-m2s6').replace("'course/m2_s5.html','course/m0_s1_foundation.html'","'course/m2_s5.html','course/m2_s6.html','course/m0_s1_foundation.html'")
extra=r'''
  await page.setViewportSize({width:1440,height:1000});await page.goto(pathToFileURL(path.join(root,'course/m2_s6.html')).href);
  const verifyData=JSON.parse(fs.readFileSync(path.join(root,'work/m2_s6/out/verification_results.json'),'utf8'));
  let verifyRouteCases=0,verifyControlCases=0;
  for(const [i,pair] of verifyData.connectivity.after.optical.expected_pairs.entries()){
    await page.locator('#verify-route').selectOption(String(i));
    const live=JSON.parse(await page.locator('#verify-route-live').getAttribute('data-result'));
    if(live.route_index!==i||JSON.stringify(live.terminals)!==JSON.stringify(pair)||!live.observed_match||live.phase_verified!==false)errors.push('M2 S6 route mismatch '+i);
    verifyRouteCases++;
  }
  for(const id of ['before','after',...verifyData.negative_controls.map(r=>r.id)]){
    await page.locator('#verify-case').selectOption(id);
    const live=JSON.parse(await page.locator('#verify-case-live').getAttribute('data-result'));
    const formal=id==='before'||id==='after',r=formal?null:verifyData.negative_controls.find(r=>r.id===id);
    const drc=formal?verifyData[id].total_records:r.drc_records,electric=formal?verifyData.connectivity[id].electrical.passed:r.electrical_passed,optical=formal?verifyData.connectivity[id].optical.passed:r.optical_passed;
    if(live.case_id!==id||live.drc_records!==drc||live.electrical_passed!==electric||live.optical_passed!==optical||live.foundry_full_signoff!==false||live.expected_fault_detected!==(formal?null:r.detected))errors.push('M2 S6 control mismatch '+id);
    verifyControlCases++;
  }
  await page.locator('#verify-name').fill('QA learner');await page.locator('#verify-drc-notes').fill('Two GDS100 markers, label-only scale, same original pre-DRC deck zero.');
  await page.locator('#verify-net-notes').fill('15 metal nets; 33 actual optical routes match declared B7 graph.');
  await page.locator('#verify-limit-notes').fill('DRC zero can still short or open; foundry signoff and optical response pending.');
  await page.locator('#verify-generate').click();const verifyNotes=JSON.parse(await page.locator('#verify-json').inputValue());
  const verifyWorksheet=verifyNotes.step==='M2 S6'&&verifyNotes.instructor_review==='pending'&&verifyNotes.learner_name==='QA learner';
  if(!verifyWorksheet)errors.push('M2 S6 worksheet mismatch');
  await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:'work/m2s6-top.png'});
  await page.locator('figure').nth(0).screenshot({path:'work/m2s6-label-fix.png'});
  await page.setViewportSize({width:390,height:844});await page.locator('#verify-route').scrollIntoViewIfNeeded();
  await page.screenshot({path:'work/m2s6-route-mobile.png'});
  await page.locator('#verify-case').scrollIntoViewIfNeeded();await page.screenshot({path:'work/m2s6-controls-mobile.png'});
  await page.screenshot({path:'work/m2s6-mobile.png',fullPage:true});
'''
src=src.replace('  const result={m2_s5_pad_cases:',extra+'\n  const result={m2_s6_route_cases:verifyRouteCases,m2_s6_control_cases:verifyControlCases,m2_s6_worksheet:verifyWorksheet,m2_s5_pad_cases:')
(ROOT/'work/m2_s6/browser_qa.cjs').write_text(src,encoding='utf-8')
