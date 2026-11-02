from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
src=(ROOT/'work/m2_s3/browser_qa.cjs').read_text(encoding='utf-8')
src=src.replace('browser-profile-m2s3','browser-profile-m2s4').replace("'course/m2_s3.html','course/m0_s1_foundation.html'","'course/m2_s3.html','course/m2_s4.html','course/m0_s1_foundation.html'")
extra=r'''
  await page.setViewportSize({width:1440,height:1000});
  await page.goto(pathToFileURL(path.join(root,'course/m2_s4.html')).href);
  const reviewData=JSON.parse(fs.readFileSync(path.join(root,'work/m2_s4/out/review_results.json'),'utf8'));
  let reviewCases=0;
  for(const image of reviewData.native_images){
    await page.locator('#review-version').selectOption(image.version);
    await page.locator('#review-scene').selectOption(image.scene);
    await page.locator('#review-mode').selectOption(image.mode);
    await page.waitForFunction(()=>{const i=document.querySelector('#review-image');return i.complete&&i.naturalWidth>0;});
    const live=JSON.parse(await page.locator('#review-live').getAttribute('data-result'));
    if(live.file!==image.file||JSON.stringify(live.layers)!==JSON.stringify(image.layers)||JSON.stringify(live.requested_box_um)!==JSON.stringify(image.requested_box_um)||live.layout_truth_replay!=='pending'||live.radius_um!==reviewData.versions[image.version].radius_um)errors.push('M2 S4 review view mismatch '+image.file);
    if(!(await page.locator('#review-image').getAttribute('src')).endsWith(image.file))errors.push('M2 S4 wrong native image '+image.file);
    reviewCases++;
  }
  await page.locator('#review-name').fill('QA learner');
  await page.locator('#review-evidence').fill('KLayout MMI, bend and thermal layers inspected.');
  await page.locator('#review-reason').fill('5 um planning minimum; 7.5 um course margin target, not a new foundry rule.');
  await page.locator('#review-handoff').fill('New output coordinates; EC/PAD/GND and phase backannotation pending.');
  await page.locator('#review-generate').click();
  const reviewNotes=JSON.parse(await page.locator('#review-json').inputValue());
  const reviewWorksheet=reviewNotes.step==='M2 S4'&&reviewNotes.instructor_review==='pending'&&reviewNotes.learner_name==='QA learner';
  if(!reviewWorksheet)errors.push('M2 S4 worksheet mismatch');
  await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:'work/m2s4-top.png'});
  await page.locator('figure').nth(1).screenshot({path:'work/m2s4-bend-comparison.png'});
  await page.locator('#review-scene').selectOption('bend');
  await page.locator('#review-mode').selectOption('combined');
  await page.setViewportSize({width:390,height:844});await page.locator('#review-version').scrollIntoViewIfNeeded();
  await page.screenshot({path:'work/m2s4-inspector-mobile.png'});
  await page.screenshot({path:'work/m2s4-mobile.png',fullPage:true});
'''
src=src.replace('  const result={m2_s3_cases:',extra+'\n  const result={m2_s4_cases:reviewCases,m2_s4_worksheet:reviewWorksheet,m2_s3_cases:')
(ROOT/'work/m2_s4/browser_qa.cjs').write_text(src,encoding='utf-8')
