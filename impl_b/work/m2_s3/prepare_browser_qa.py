from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
src=(ROOT/'work/m2_s2/browser_qa.cjs').read_text(encoding='utf-8')
src=src.replace('browser-profile-m2s2','browser-profile-m2s3').replace("'course/m2_s2.html','course/m0_s1_foundation.html'","'course/m2_s2.html','course/m2_s3.html','course/m0_s1_foundation.html'")
extra=r'''
  await page.setViewportSize({width:1440,height:1000});
  await page.goto(pathToFileURL(path.join(root,'course/m2_s3.html')).href);
  const layoutInfo=JSON.parse(fs.readFileSync(path.join(root,'work/m2_s3/out/layout_info.json'),'utf8'));
  const physicalPhases=JSON.parse(fs.readFileSync(path.join(root,'phase_settings.json'),'utf8'));
  let layoutCases=0;
  for(const gate of Object.keys(physicalPhases.programs)){
    await page.locator('#layout-gate').selectOption(gate);
    for(const region of layoutInfo.phase_regions){
      await page.locator('#layout-instance').selectOption(region.instance);
      await page.locator('#layout-phase').selectOption(region.parameter);
      const live=JSON.parse(await page.locator('#layout-live').getAttribute('data-result'));
      const place=layoutInfo.placement.find(p=>p.id===region.instance);
      const rad=physicalPhases.programs[gate][physicalPhases.channel_order.indexOf(region.channel)];
      if(live.channel!==region.channel||JSON.stringify(live.origin_um)!==JSON.stringify(place.origin_um)||JSON.stringify(live.center_um)!==JSON.stringify(region.center_um)||JSON.stringify(live.contacts)!==JSON.stringify(region.local_contacts)||live.phase_rad!==rad||live.pad_id!==null||live.voltage_calibration!==null)errors.push('M2 S3 coordinate/phase mismatch '+gate+' '+region.channel);
      const highlightX=Number(await page.locator('#layout-unit rect').getAttribute('x'));
      const local=layoutInfo.unit.controls.find(c=>c.parameter===region.parameter);
      if(highlightX!==local.heated_start_um-2)errors.push('M2 S3 highlight mismatch');
      layoutCases++;
    }
  }
  await page.locator('#layout-name').fill('QA learner');
  await page.locator('#layout-placement-notes').fill('Seven MZIs in four columns; six bypass segments.');
  await page.locator('#layout-phase-notes').fill('Local contacts are not probe PADs; length phase backannotation pending.');
  await page.locator('#layout-review-notes').fill('KLayout GDS readback, then M2 S4 bend and gap review.');
  await page.locator('#layout-generate').click();
  const layoutNotes=JSON.parse(await page.locator('#layout-json').inputValue());
  const layoutWorksheet=layoutNotes.step==='M2 S3'&&layoutNotes.instructor_review==='pending'&&layoutNotes.learner_name==='QA learner';
  if(!layoutWorksheet)errors.push('M2 S3 worksheet mismatch');
  await page.evaluate(()=>window.scrollTo(0,0));
  await page.screenshot({path:'work/m2s3-top.png'});
  for(const [i,name] of ['mzi','mmi-contacts','b7'].entries())await page.locator('figure').nth(i).screenshot({path:'work/m2s3-'+name+'.png'});
  await page.locator('#layout-unit').screenshot({path:'work/m2s3-interactive-unit.png'});
  await page.setViewportSize({width:390,height:844});
  await page.locator('#layout-instance').scrollIntoViewIfNeeded();
  await page.screenshot({path:'work/m2s3-inspector-mobile.png'});
  await page.screenshot({path:'work/m2s3-mobile.png',fullPage:true});
'''
src=src.replace('  const result={m2_s2_cases:',extra+'\n  const result={m2_s3_cases:layoutCases,m2_s3_worksheet:layoutWorksheet,m2_s2_cases:')
(ROOT/'work/m2_s3/browser_qa.cjs').write_text(src,encoding='utf-8')
