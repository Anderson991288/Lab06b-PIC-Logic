from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
src=(ROOT/'work/m2_s7/browser_qa.cjs').read_text(encoding='utf-8')
src=src.replace('browser-profile-m2s7','browser-profile-m3s1').replace("'course/m2_s7.html','course/m0_s1_foundation.html'","'course/m2_s7.html','course/m3_s1.html','course/m0_s1_foundation.html'")
extra=r'''
  await page.setViewportSize({width:1440,height:1000});await page.goto(pathToFileURL(path.join(root,'course/m3_s1.html')).href);
  const rebuildData=JSON.parse(fs.readFileSync(path.join(root,'work/m3_s1/out/rebuild_results.json'),'utf8'));
  let rebuildChecks=0,rebuildTruthCases=0;
  for(const b of rebuildData.builds){
    await page.locator('#rebuild-build').selectOption(b.build);
    for(const [i,c] of b.checks.entries()){
      await page.locator('#rebuild-check').selectOption(String(i));
      const live=JSON.parse(await page.locator('#rebuild-check-live').getAttribute('data-result'));
      if(live.build!==b.build||live.check_index!==i||live.name!==c.name||live.passed!==c.passed||live.raw_sha_identical!==b.raw_sha_identical||live.normalized_sha_identical!==(b.normalized.sha256===b.reference_normalized.sha256)||live.physical_function_qualified!==false)errors.push('M3 S1 acceptance mismatch '+b.build+' '+i);
      rebuildChecks++;
    }
    const cases=JSON.parse(fs.readFileSync(path.join(root,'work/m3_s1/out/build_'+b.build+'/replay.json'),'utf8')).cases;
    for(const [id,value] of Object.entries(cases)){
      await page.locator('#rebuild-case').selectOption(id);
      for(const g of ['AND2','OR2','XOR2','AND4','OR4']){
        await page.locator('#rebuild-gate').selectOption(g);
        for(let i=0;i<16;i++){
          await page.locator('#rebuild-pattern').selectOption(String(i));
          const live=JSON.parse(await page.locator('#rebuild-truth-live').getAttribute('data-result')),row=value.rows.find(r=>r.gate===g&&r.index_lsb_x1===i);
          if(live.build!==b.build||live.case_id!==id||live.gate!==g||live.pattern!==row.pattern||live.expected!==row.expected||live.bit!==row.bit||live.passed!==row.passed||Math.abs(live.delta-row.delta)>1e-12||Math.abs(live.signed_margin-row.signed_margin)>1e-12||JSON.stringify(live.powers)!==JSON.stringify(row.powers)||live.physical_function_qualified!==false)errors.push('M3 S1 truth mismatch '+b.build+' '+id+' '+g+' '+i);
          rebuildTruthCases++;
        }
      }
    }
  }
  await page.locator('#rebuild-name').fill('QA learner');await page.locator('#rebuild-source-notes').fill('Two empty targets; authored sources plus design inputs; preinstalled licensed tools.');
  await page.locator('#rebuild-hash-notes').fill('Raw SHA differs; timestamp-only SHA and all-layer XOR/text match; actual added Si detected.');
  await page.locator('#rebuild-truth-notes').fill('All 400 cases match S7 in each build; physical calibration and foundry signoff pending.');
  await page.locator('#rebuild-generate').click();const rebuildNotes=JSON.parse(await page.locator('#rebuild-json').inputValue());
  const rebuildWorksheet=rebuildNotes.step==='M3 S1'&&rebuildNotes.learner_name==='QA learner'&&rebuildNotes.instructor_review==='pending'&&rebuildNotes.physical_function_qualified===false;
  if(!rebuildWorksheet)errors.push('M3 S1 worksheet mismatch');
  await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:'work/m3s1-top.png'});
  await page.locator('figure').nth(0).screenshot({path:'work/m3s1-pipeline.png'});await page.locator('figure').nth(1).screenshot({path:'work/m3s1-timings.png'});
  await page.setViewportSize({width:390,height:844});await page.locator('#rebuild-build').scrollIntoViewIfNeeded();await page.screenshot({path:'work/m3s1-check-mobile.png'});
  await page.locator('#rebuild-case').scrollIntoViewIfNeeded();await page.screenshot({path:'work/m3s1-truth-mobile.png'});
  await page.screenshot({path:'work/m3s1-mobile.png',fullPage:true});
'''
src=src.replace('  const result={m2_s7_replay_cases:',extra+'\n  const result={m3_s1_acceptance_cases:rebuildChecks,m3_s1_truth_cases:rebuildTruthCases,m3_s1_worksheet:rebuildWorksheet,m2_s7_replay_cases:')
(ROOT/'work/m3_s1/browser_qa.cjs').write_text(src,encoding='utf-8')
