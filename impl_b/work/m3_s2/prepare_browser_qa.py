from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
src=(ROOT/'work/m3_s1/browser_qa.cjs').read_text(encoding='utf-8')
src=src.replace('browser-profile-m3s1','browser-profile-m3s2').replace("'course/m3_s1.html','course/m0_s1_foundation.html'","'course/m3_s1.html','course/m3_s2.html','course/m0_s1_foundation.html'")
extra=r'''
  await page.setViewportSize({width:1440,height:1000});await page.goto(pathToFileURL(path.join(root,'course/m3_s2.html')).href);
  const geomIndependent=JSON.parse(fs.readFileSync(path.join(root,'work/m3_s2/out/independent_results.json'),'utf8'));
  const geomNative=JSON.parse(fs.readFileSync(path.join(root,'work/m3_s2/out/klayout_results.json'),'utf8'));
  const geomDifference=JSON.parse(fs.readFileSync(path.join(root,'work/m3_s2/out/method_difference.json'),'utf8'));
  let geomCases=0,geomMethods=0;
  for(const c of geomIndependent){
    await page.locator('#geometry-case').selectOption(c.id);
    for(const l of c.layers){
      await page.locator('#geometry-layer').selectOption(String(l.layer));
      for(const kind of ['width','space']){
        await page.locator('#geometry-kind').selectOption(kind);
        const live=JSON.parse(await page.locator('#geometry-live').getAttribute('data-result')),x=l.measurements[kind],k=geomNative.find(a=>a.id===c.id).layers.find(a=>a.layer===l.layer).metrics[kind];
        if(live.case_id!==c.id||live.layer!==l.layer||live.kind!==kind||live.independent_um!==x.minimum.value_um||live.visibility!==x.minimum.visibility||JSON.stringify(live.point_A_um)!==JSON.stringify(x.minimum.point_A_um)||JSON.stringify(live.point_B_um)!==JSON.stringify(x.minimum.point_B_um)||live.effective_limit_um!==x.effective_limit_um||live.independent_rule_passed!==x.rule_passed||live.KLayout_rule_passed!==k.rule_passed||live.KLayout_violations!==k.violations||live.KLayout_lower_um!==(k.lower_bound_um??null)||live.KLayout_upper_um!==(k.upper_bound_um??null)||live.physical_function_qualified!==false)errors.push('M3 S2 geometry mismatch '+c.id+' '+l.layer+' '+kind);
        geomCases++;
      }
    }
  }
  for(const method of ['strict','corrected']){
    await page.locator('#geometry-method').selectOption(method);const live=JSON.parse(await page.locator('#geometry-method-live').getAttribute('data-result'));
    if(live.method!==method||live.Si_space_um!==(method==='strict'?geomDifference.strict_connector_only_um:geomDifference.corrected_um)||live.numeric_agreement!==(method==='corrected')||live.physical_function_qualified!==false)errors.push('M3 S2 method mismatch '+method);geomMethods++;
  }
  await page.locator('#geometry-name').fill('QA learner');await page.locator('#geometry-measure-notes').fill('Independent GDS reader; 6 coordinate witnesses; nominal and effective limits separated.');
  await page.locator('#geometry-difference-notes').fill('Closed notch boundary limit 0.530 um; strict disjoint missed cap; 8 real GDS controls.');
  await page.locator('#geometry-limit-notes').fill('Selected checks only, not full foundry signoff; learner independent submission and instructor review pending.');
  await page.locator('#geometry-generate').click();const geomNotes=JSON.parse(await page.locator('#geometry-json').inputValue());
  const geomWorksheet=geomNotes.step==='M3 S2'&&geomNotes.learner_name==='QA learner'&&geomNotes.instructor_review==='pending'&&geomNotes.physical_function_qualified===false;
  if(!geomWorksheet)errors.push('M3 S2 worksheet mismatch');
  await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:'work/m3s2-top.png'});
  await page.locator('figure').nth(0).screenshot({path:'work/m3s2-comparison.png'});await page.locator('figure').nth(1).screenshot({path:'work/m3s2-witnesses.png'});
  await page.setViewportSize({width:390,height:844});await page.locator('#geometry-method').scrollIntoViewIfNeeded();await page.screenshot({path:'work/m3s2-method-mobile.png'});
  await page.locator('#geometry-case').scrollIntoViewIfNeeded();await page.screenshot({path:'work/m3s2-case-mobile.png'});await page.screenshot({path:'work/m3s2-mobile.png',fullPage:true});
'''
src=src.replace('  const result={m3_s1_acceptance_cases:',extra+'\n  const result={m3_s2_geometry_cases:geomCases,m3_s2_method_cases:geomMethods,m3_s2_worksheet:geomWorksheet,m3_s1_acceptance_cases:')
(ROOT/'work/m3_s2/browser_qa.cjs').write_text(src,encoding='utf-8')
