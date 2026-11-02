from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
src=(ROOT/'work/m2_s6/browser_qa.cjs').read_text(encoding='utf-8')
src=src.replace('browser-profile-m2s6','browser-profile-m2s7').replace("'course/m2_s6.html','course/m0_s1_foundation.html'","'course/m2_s6.html','course/m2_s7.html','course/m0_s1_foundation.html'")
extra=r'''
  await page.setViewportSize({width:1440,height:1000});await page.goto(pathToFileURL(path.join(root,'course/m2_s7.html')).href);
  const deliveryData=JSON.parse(fs.readFileSync(path.join(root,'work/m2_s7/out/replay_results.json'),'utf8'));
  const deliveryPaths=JSON.parse(fs.readFileSync(path.join(root,'work/m2_s7/out/paths.json'),'utf8'));
  let deliveryCases=0,deliveryPathCases=0;
  for(const [id,value] of Object.entries(deliveryData.cases)){
    await page.locator('#delivery-case').selectOption(id);
    for(const gate of Object.keys(value.functions)){
      await page.locator('#delivery-gate').selectOption(gate);
      for(let i=0;i<16;i++){
        await page.locator('#delivery-pattern').selectOption(String(i));
        const live=JSON.parse(await page.locator('#delivery-live').getAttribute('data-result')),row=value.rows.find(r=>r.gate===gate&&r.index_lsb_x1===i);
        if(live.case_id!==id||live.gate!==gate||live.pattern!==row.pattern||live.expected!==row.expected||live.bit!==row.bit||live.passed!==row.passed||Math.abs(live.delta-row.delta)>1e-12||Math.abs(live.signed_margin-row.signed_margin)>1e-12||JSON.stringify(live.powers)!==JSON.stringify(row.powers)||live.physical_function_qualified!==false)errors.push('M2 S7 replay mismatch '+id+' '+gate+' '+i);
        deliveryCases++;
      }
    }
  }
  for(const [i,p] of deliveryPaths.paths.entries()){
    await page.locator('#delivery-path').selectOption(String(i));
    const live=JSON.parse(await page.locator('#delivery-path-live').getAttribute('data-result')),route=deliveryPaths.routes.find(r=>r.component===p.gds_route_component);
    if(live.id!==p.id||live.length_um!==p.length_um||live.gds_route_component!==p.gds_route_component||JSON.stringify(live.terminals)!==JSON.stringify(route.terminals)||live.in_core_replay!==(p.source_class==='core')||live.optical_PEX_or_calibrated_lengths!==false)errors.push('M2 S7 path mismatch '+i);
    deliveryPathCases++;
  }
  await page.locator('#delivery-name').fill('QA learner');await page.locator('#delivery-path-notes').fill('58 core plus 10 fan; 33 actual GDS connections; core reference plane.');
  await page.locator('#delivery-replay-notes').fill('Original phases 53/80 after length; analytic model candidate 80/80; relocated replay matches.');
  await page.locator('#delivery-limit-notes').fill('EC, MMI absolute phase, heater voltage and foundry signoff pending.');
  await page.locator('#delivery-generate').click();const deliveryNotes=JSON.parse(await page.locator('#delivery-json').inputValue());
  const deliveryWorksheet=deliveryNotes.step==='M2 S7'&&deliveryNotes.learner_name==='QA learner'&&deliveryNotes.instructor_review==='pending'&&deliveryNotes.physical_function_qualified===false;
  if(!deliveryWorksheet)errors.push('M2 S7 worksheet mismatch');
  await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:'work/m2s7-top.png'});
  await page.locator('figure').nth(2).screenshot({path:'work/m2s7-replay.png'});
  await page.locator('figure').nth(3).screenshot({path:'work/m2s7-sensitivity.png'});
  await page.locator('#delivery-case').selectOption('length_original');await page.locator('#delivery-gate').selectOption('XOR2');await page.locator('#delivery-pattern').selectOption('0');
  await page.setViewportSize({width:390,height:844});await page.locator('#delivery-case').scrollIntoViewIfNeeded();await page.screenshot({path:'work/m2s7-case-mobile.png'});
  await page.locator('#delivery-path').scrollIntoViewIfNeeded();await page.screenshot({path:'work/m2s7-path-mobile.png'});
  await page.screenshot({path:'work/m2s7-mobile.png',fullPage:true});
'''
src=src.replace('  const result={m2_s6_route_cases:',extra+'\n  const result={m2_s7_replay_cases:deliveryCases,m2_s7_path_cases:deliveryPathCases,m2_s7_worksheet:deliveryWorksheet,m2_s6_route_cases:')
(ROOT/'work/m2_s7/browser_qa.cjs').write_text(src,encoding='utf-8')
