from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
src=(ROOT/'work/m2_s4/browser_qa.cjs').read_text(encoding='utf-8')
src=src.replace('browser-profile-m2s4','browser-profile-m2s5').replace("'course/m2_s4.html','course/m0_s1_foundation.html'","'course/m2_s4.html','course/m2_s5.html','course/m0_s1_foundation.html'")
extra=r'''
  await page.setViewportSize({width:1440,height:1000});await page.goto(pathToFileURL(path.join(root,'course/m2_s5.html')).href);
  const chipInfo=JSON.parse(fs.readFileSync(path.join(root,'work/m2_s5/out/chip_info.json'),'utf8'));
  const chipRead=JSON.parse(fs.readFileSync(path.join(root,'work/m2_s5/out/chip_readback.json'),'utf8'));
  const chipPhases=JSON.parse(fs.readFileSync(path.join(root,'phase_settings.json'),'utf8'));
  let chipPadCases=0,chipOpticalCases=0;
  for(const gate of Object.keys(chipPhases.programs)){
    await page.locator('#chip-gate').selectOption(gate);
    for(const p of chipInfo.pads){
      await page.locator('#chip-pad').selectOption(p.pad_id);
      const live=JSON.parse(await page.locator('#chip-live').getAttribute('data-result'));
      const channel=p.channel||null,phase=channel===null?null:chipPhases.programs[gate][chipPhases.channel_order.indexOf(channel)];
      if(live.pad_id!==p.pad_id||live.channel!==channel||live.phase_rad!==phase||live.voltage!==null||live.metal_component!==chipRead.pad_components[p.pad_id][0]||JSON.stringify(live.center_um)!==JSON.stringify(p.center_um)||live.drive_endpoint!==(p.drive_endpoint||null)||live.return_endpoint!==(p.return_endpoint||null))errors.push('M2 S5 pad mismatch '+gate+' '+p.pad_id);
      chipPadCases++;
    }
  }
  for(const p of chipInfo.optical_io){
    await page.locator('#chip-optical').selectOption(p.interface_id);
    const live=JSON.parse(await page.locator('#chip-optical-live').getAttribute('data-result'));
    if(JSON.stringify(live)!==JSON.stringify(p))errors.push('M2 S5 optical mismatch '+p.interface_id);
    chipOpticalCases++;
  }
  await page.locator('#chip-name').fill('QA learner');await page.locator('#chip-io-notes').fill('Reference EC, normalized amplitudes at core plane.');
  await page.locator('#chip-pad-notes').fill('Driver to PAD to A, heater to B to stepped GND; 16 PADs, 15 metal nets.');
  await page.locator('#chip-pending-notes').fill('EC response, full DRC/LVS, bias calibration and path phase replay pending.');
  await page.locator('#chip-generate').click();const chipNotes=JSON.parse(await page.locator('#chip-json').inputValue());
  const chipWorksheet=chipNotes.step==='M2 S5'&&chipNotes.instructor_review==='pending'&&chipNotes.learner_name==='QA learner';
  if(!chipWorksheet)errors.push('M2 S5 worksheet mismatch');
  await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:'work/m2s5-top.png'});
  await page.locator('figure').nth(0).screenshot({path:'work/m2s5-chip.png'});
  await page.locator('figure').nth(2).screenshot({path:'work/m2s5-return.png'});
  await page.setViewportSize({width:390,height:844});await page.locator('#chip-pad').scrollIntoViewIfNeeded();
  await page.screenshot({path:'work/m2s5-inspector-mobile.png'});await page.screenshot({path:'work/m2s5-mobile.png',fullPage:true});
'''
src=src.replace('  const result={m2_s4_cases:',extra+'\n  const result={m2_s5_pad_cases:chipPadCases,m2_s5_optical_cases:chipOpticalCases,m2_s5_worksheet:chipWorksheet,m2_s4_cases:')
(ROOT/'work/m2_s5/browser_qa.cjs').write_text(src,encoding='utf-8')
