from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
src=(ROOT/'work/m2_s1/browser_qa.cjs').read_text(encoding='utf-8')
src=src.replace('browser-profile-m2s1','browser-profile-m2s2').replace("'course/m2_s1.html','course/m0_s1_foundation.html'","'course/m2_s1.html','course/m2_s2.html','course/m0_s1_foundation.html'")
extra=r'''
  await page.setViewportSize({width:1440,height:1000});
  await page.goto(pathToFileURL(path.join(root,'course/m2_s2.html')).href);
  const pdkCases=JSON.parse(fs.readFileSync(path.join(root,'work/m2_s2/out/comparison.json'),'utf8'));
  let pdkCaseCount=0;
  for(const [gate,rows] of Object.entries(pdkCases)){
    await page.locator('#pdk-gate').selectOption(gate);
    for(const r of rows){
      await page.locator('#pdk-pattern').selectOption(r.pattern);
      const live=JSON.parse(await page.locator('#pdk-live').getAttribute('data-result'));
      if(JSON.stringify(live)!==JSON.stringify(r))errors.push('M2 S2 case mismatch '+gate+' '+r.pattern);
      if(await page.locator('#pdk-power tbody tr').count()!==5)errors.push('M2 S2 output coverage mismatch');
      if(await page.locator('#pdk-matrix tbody tr').count()!==5)errors.push('M2 S2 matrix coverage mismatch');
      pdkCaseCount++;
    }
  }
  await page.locator('#pdk-name').fill('QA learner');
  await page.locator('#pdk-mapping-notes').fill('Upper in2/out2; phi before MMI1, theta upper arm.');
  await page.locator('#pdk-comparison-notes').fill('80 cases, fixed phases, delta from coherent fields.');
  await page.locator('#pdk-scope-notes').fill('Default ideal Coupler2x2Model; length and thermal calibration pending.');
  await page.locator('#pdk-generate').click();
  const pdkNotes=JSON.parse(await page.locator('#pdk-json').inputValue());
  const pdkWorksheet=pdkNotes.step==='M2 S2'&&pdkNotes.instructor_review==='pending'&&pdkNotes.learner_name==='QA learner';
  if(!pdkWorksheet)errors.push('M2 S2 worksheet mismatch');
  await page.screenshot({path:'work/m2s2-top.png'});
  await page.locator('figure').nth(0).screenshot({path:'work/m2s2-mzi.png'});
  await page.locator('figure').nth(1).screenshot({path:'work/m2s2-comparison.png'});
  await page.setViewportSize({width:390,height:844});
  await page.locator('#pdk-gate').scrollIntoViewIfNeeded();
  await page.screenshot({path:'work/m2s2-inspector-mobile.png'});
  await page.screenshot({path:'work/m2s2-mobile.png',fullPage:true});
'''
src=src.replace('  const result={status:errors.length?',extra+'\n  const result={m2_s2_cases:pdkCaseCount,m2_s2_worksheet:pdkWorksheet,status:errors.length?')
(ROOT/'work/m2_s2/browser_qa.cjs').write_text(src,encoding='utf-8')
