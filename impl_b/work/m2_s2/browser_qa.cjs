const {chromium} = require('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1029-1117-0_26.1029.1117.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules/playwright');
const fs = require('fs');
const path = require('path');
const {pathToFileURL} = require('url');
const root = path.resolve(process.argv[2] || 'outputs/Lab06b');
(async()=>{
  const browser=await chromium.launchPersistentContext(path.resolve('work/browser-profile-m2s2'),{headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--disable-crash-reporter']});
  const page=await browser.newPage({viewport:{width:1440,height:1000},deviceScaleFactor:1});
  const errors=[];page.on('pageerror',e=>errors.push(String(e)));
  const checked=[];
  for(const file of ['Lab06b_index.html','course/plan.html','course/m0_s1.html','course/m0_s2.html','course/m0_s3.html','course/m1_s1.html','course/m1_s2.html','course/m1_s3.html','course/m1_s4.html','course/m1_s5.html','course/m2_s1.html','course/m2_s2.html','course/m0_s1_foundation.html','analysis/lab01a_7_6.html','reference/source_context.html','reference/C01/reader.html']){
    await page.goto(pathToFileURL(path.join(root,file)).href);
    await page.waitForLoadState('load');
    const images=await page.locator('img').evaluateAll(imgs=>imgs.filter(x=>!x.complete||x.naturalWidth===0).map(x=>x.src));
    if(images.length)errors.push(file+': broken images '+images.join(','));
    const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth+1);
    if(overflow)errors.push(file+': desktop page overflow');
    checked.push({file,images:await page.locator('img').count(),desktop_overflow:overflow});
    if(file==='course/m1_s1.html')await page.screenshot({path:'work/m1s1-desktop.png',fullPage:true});
    if(file==='course/m0_s3.html')await page.screenshot({path:'work/m0s3-desktop.png',fullPage:true});
    if(file==='Lab06b_index.html')await page.screenshot({path:'work/home-desktop.png',fullPage:true});
    if(file==='analysis/lab01a_7_6.html')await page.screenshot({path:'work/field-desktop.png',fullPage:true});
  }
  await page.goto(pathToFileURL(path.join(root,'course/m0_s1_foundation.html')).href);
  for(const [mode,angle,want] of [['single',0,0],['single',0.5,0.5],['single',1,1],['anti',0.5,1],['same',0.5,0]]){
    await page.locator('#input-mode').selectOption(mode);
    await page.locator('#theta').fill(String(angle));
    await page.locator('#theta').dispatchEvent('input');
    const value=await page.locator('#live-result').innerText();
    const p=Number(value.match(/out1\) = ([\d.]+)/)[1]);
    if(Math.abs(p-want)>1e-6)errors.push('interactive mismatch: '+mode+' '+angle+' '+value);
  }
  await page.locator('#learner-name').fill('QA learner');
  await page.locator('#learner-python').fill('Python 3.13 QA');
  await page.locator('#learner-notes').fill('Power and phase observation test');
  await page.locator('#generate-notes').click();
  const data=JSON.parse(await page.locator('#notes-json').inputValue());
  if(data.learner_name!=='QA learner'||data.step!=='M0 S1')errors.push('learner JSON mismatch');
  await page.screenshot({path:'work/m0-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  for(const file of ['Lab06b_index.html','course/plan.html','course/m0_s1.html','course/m0_s2.html','course/m0_s3.html','course/m1_s1.html','course/m1_s2.html','course/m1_s3.html','course/m1_s4.html','course/m1_s5.html','course/m2_s1.html','course/m2_s2.html','course/m0_s1_foundation.html','analysis/lab01a_7_6.html']){
    await page.goto(pathToFileURL(path.join(root,file)).href);
    const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth+1);
    if(overflow)errors.push(file+': mobile page overflow');
    checked.push({file,mobile_overflow:overflow});
    if(file==='course/m0_s1.html')await page.screenshot({path:'work/m0-mobile.png',fullPage:true});
  }
  await page.goto(pathToFileURL(path.join(root,'course/m0_s2.html')).href);
  await page.locator('#s2-name').fill('QA learner');
  await page.locator('#s2-notes').fill('Mode index, convergence and data provenance.');
  await page.locator('#s2-generate').click();
  const s2Data=JSON.parse(await page.locator('#s2-json').inputValue());
  if(s2Data.step!=='M0 S2'||s2Data.instructor_review!=='pending')errors.push('M0 S2 worksheet mismatch');
  await page.screenshot({path:'work/m0s2-mobile.png',fullPage:true});
  await page.goto(pathToFileURL(path.join(root,'course/m0_s3.html')).href);
  const samples=JSON.parse(fs.readFileSync(path.join(root,'work/m0_s3/out/model_results.json'),'utf8')).interactive_samples;
  for(const sample of samples){
    await page.locator('#s3-input').selectOption(sample.input);
    await page.locator('#s3-theta').fill(String(sample.theta_pi));
    await page.locator('#s3-phi').fill(String(sample.phi_pi));
    await page.locator('#s3-theta').dispatchEvent('input');
    const text=await page.locator('#s3-power').innerText();
    const power=Number(text.match(/upper\) = ([\d.]+)/)[1]);
    if(Math.abs(power-sample.power[0])>1e-6)errors.push('M0 S3 interactive mismatch '+JSON.stringify(sample));
  }
  await page.locator('#s3-name').fill('QA learner');
  await page.locator('#s3-notes').fill('Port order, matrix phase, power loss and controlled mutation.');
  await page.locator('#s3-generate').click();
  const s3Data=JSON.parse(await page.locator('#s3-json').inputValue());
  if(s3Data.step!=='M0 S3'||s3Data.instructor_review!=='pending')errors.push('M0 S3 worksheet mismatch');
  await page.screenshot({path:'work/m0s3-mobile.png',fullPage:true});
  await page.goto(pathToFileURL(path.join(root,'course/m1_s1.html')).href);
  const logicSamples=JSON.parse(fs.readFileSync(path.join(root,'work/m1_s1/out/encoding_results.json'),'utf8')).interactive_samples;
  for(const sample of logicSamples){
    await page.locator('#logic-kind').selectOption(sample.kind);
    await page.locator('#logic-bits').selectOption(sample.bits.join(''));
    await page.locator('#logic-phase').fill(String(sample.phase_pi));
    if(sample.kind==='NAND2')await page.locator('#logic-reference').fill(String(sample.amplitude));
    await page.locator('#logic-phase').dispatchEvent('input');
    const actual=JSON.parse(await page.locator('#logic-result').getAttribute('data-result'));
    if(actual.powers.length!==sample.output_powers.length||actual.powers.some((p,i)=>Math.abs(p-sample.output_powers[i])>1e-10))errors.push('M1 S1 powers mismatch '+JSON.stringify(sample));
    if(actual.bit!==sample.readout.bit||Math.abs(actual.margin-sample.readout.margin)>1e-10)errors.push('M1 S1 decision mismatch '+JSON.stringify(sample));
  }
  await page.locator('#m1-name').fill('QA learner');
  await page.locator('#m1-encoding').fill('[1,1,0,0,3], PR=9, total=11, read out1-out3');
  await page.locator('#m1-observation').fill('Relative phase changes interference; fixed threshold and power unit.');
  await page.locator('#m1-generate').click();
  const m1data=JSON.parse(await page.locator('#m1-json').inputValue());
  const m1worksheet=m1data.step==='M1 S1'&&m1data.instructor_review==='pending'&&m1data.learner_name==='QA learner'&&m1data.encoding_and_ports.includes('total=11');
  if(!m1worksheet)errors.push('M1 S1 learner worksheet mismatch');
  await page.screenshot({path:'work/m1s1-mobile.png',fullPage:true});
  await page.goto(pathToFileURL(path.join(root,'course/m1_s2.html')).href);
  const b7Samples=JSON.parse(fs.readFileSync(path.join(root,'work/m1_s2/out/b7_results.json'),'utf8')).interactive_samples;
  for(const sample of b7Samples){
    await page.locator('#b7-profile').selectOption(sample.profile);
    await page.locator('#b7-source').selectOption(sample.source);
    if(!sample.source.startsWith('basis'))await page.locator('#b7-reference').fill(String(sample.reference_amplitude));
    await page.locator('#b7-stage').fill(String(sample.step));
    await page.locator('#b7-stage').dispatchEvent('input');
    const actual=JSON.parse(await page.locator('#b7-live').getAttribute('data-result'));
    if(actual.field.some((z,i)=>z.some((part,k)=>Math.abs(part-sample.field[i][k])>1e-11)))errors.push('B7 field mismatch '+JSON.stringify(sample));
    if(actual.powers.some((p,i)=>Math.abs(p-sample.powers[i])>1e-10))errors.push('B7 power mismatch '+JSON.stringify(sample));
  }
  // Changing R scales its field, and remains disabled for genuine basis probes.
  await page.locator('#b7-profile').selectOption('identity_all');
  await page.locator('#b7-source').selectOption('1000');
  await page.locator('#b7-reference').fill('2');
  await page.locator('#b7-reference').dispatchEvent('input');
  await page.locator('#b7-stage').fill('4');await page.locator('#b7-stage').dispatchEvent('input');
  const rCheck=JSON.parse(await page.locator('#b7-live').getAttribute('data-result'));
  if(Math.abs(rCheck.total-5)>1e-10||Math.abs(rCheck.powers[4]-4)>1e-10)errors.push('B7 reference amplitude/power mismatch');
  await page.locator('#b7-source').selectOption('basis4');
  if(!await page.locator('#b7-reference').isDisabled())errors.push('Basis probe must disable R control');
  await page.locator('#b7-name').fill('QA learner');
  await page.locator('#b7-wiring-notes').fill('L3 L2 L1 L0, six bypasses; read out1-out3');
  await page.locator('#b7-observations').fill('Five probes reconstruct columns; unitarity alone does not prove wiring.');
  await page.locator('#b7-generate').click();
  const b7data=JSON.parse(await page.locator('#b7-json').inputValue());
  const b7worksheet=b7data.step==='M1 S2'&&b7data.instructor_review==='pending'&&b7data.wiring_and_order.includes('six bypasses');
  if(!b7worksheet)errors.push('M1 S2 worksheet mismatch');
  await page.screenshot({path:'work/m1s2-mobile.png',fullPage:true});
  await page.setViewportSize({width:1440,height:1000});await page.goto(pathToFileURL(path.join(root,'course/m1_s2.html')).href);
  await page.screenshot({path:'work/m1s2-top.png'});
  await page.locator('figure').first().screenshot({path:'work/m1s2-map.png'});
  await page.goto(pathToFileURL(path.join(root,'course/m1_s3.html')).href);
  const readSamples=JSON.parse(fs.readFileSync(path.join(root,'work/m1_s3/out/readout_results.json'),'utf8')).interactive_samples;
  for(const sample of readSamples){
    await page.locator('#read-pattern').selectOption(sample.pattern);
    await page.locator('#read-R').fill(String(sample.reference_amplitude));
    await page.locator('#read-reference-phase').fill(String(sample.reference_phase_pi));
    await page.locator('#read-data-phase').fill(String(sample.x2_phase_pi));
    await page.locator('#read-threshold').fill(String(sample.threshold));
    await page.locator('#read-threshold').dispatchEvent('input');
    const actual=JSON.parse(await page.locator('#read-live').getAttribute('data-result'));
    const expected=sample.result;
    for(const [key,want] of [['plus',expected.positive],['minus',expected.negative]]){
      if(actual[key].terms.some((z,i)=>z.some((part,k)=>Math.abs(part-want.terms[i][k])>1e-11)))errors.push('M1 S3 weighted term mismatch '+sample.pattern);
      for(const [gotKey,wantKey] of [['power','power'],['self','self_power'],['interference','interference_power']]){
        if(Math.abs(actual[key][gotKey]-want[wantKey])>1e-10)errors.push('M1 S3 power decomposition mismatch '+sample.pattern);
      }
    }
    if(actual.powers.some((p,i)=>Math.abs(p-expected.output_powers[i])>1e-10)||actual.bit!==expected.readout.bit||Math.abs(actual.delta-expected.readout.delta)>1e-10)errors.push('M1 S3 decision mismatch '+JSON.stringify(sample));
  }
  const readCurrent=JSON.parse(await page.locator('#read-live').getAttribute('data-result'));
  await page.locator('#read-threshold').fill(String(readCurrent.delta));
  await page.locator('#read-threshold').dispatchEvent('input');
  const exactBoundary=JSON.parse(await page.locator('#read-live').getAttribute('data-result'));
  if(exactBoundary.bit!==null||Math.abs(exactBoundary.margin)>1e-10)errors.push('M1 S3 exact threshold must remain boundary');
  await page.locator('#read-threshold').fill('');await page.locator('#read-threshold').dispatchEvent('input');
  if(await page.locator('#read-live').getAttribute('data-result'))errors.push('M1 S3 empty threshold must not retain a stale result');
  await page.locator('#read-threshold').fill('0');await page.locator('#read-threshold').dispatchEvent('input');
  await page.locator('#read-name').fill('QA learner');
  await page.locator('#read-hand1000').fill('Complex row sum then modulus squared; delta<0, bit 0.');
  await page.locator('#read-hand1100').fill('Complex row sum then modulus squared; delta>0, bit 1.');
  await page.locator('#read-observations').fill('Interference terms retained; epsilon boundary is not a valid bit.');
  await page.locator('#read-generate').click();
  const readData=JSON.parse(await page.locator('#read-json').inputValue());
  const readWorksheet=readData.step==='M1 S3'&&readData.instructor_review==='pending'&&readData.hand_calculation_1000.includes('bit 0')&&readData.hand_calculation_1100.includes('bit 1');
  if(!readWorksheet)errors.push('M1 S3 learner worksheet mismatch');
  await page.screenshot({path:'work/m1s3-top.png',fullPage:false});
  await page.setViewportSize({width:390,height:844});await page.screenshot({path:'work/m1s3-mobile.png',fullPage:true});
  await page.goto(pathToFileURL(path.join(root,'course/m1_s4.html')).href);
  const logicData=JSON.parse(fs.readFileSync(path.join(root,'work/m1_s4/out/logic_results.json'),'utf8'));
  let logicCases=0;
  async function verifyGate(gate,pattern,R,phase,thetaError,expected){
    await page.locator('#gate-program').selectOption(gate);
    await page.locator('#gate-pattern').selectOption(pattern);
    await page.locator('#gate-R').fill(String(R));
    await page.locator('#gate-phase').fill(String(phase));
    await page.locator('#gate-error').fill(String(thetaError));
    await page.locator('#gate-error').dispatchEvent('input');
    const actual=JSON.parse(await page.locator('#gate-live').getAttribute('data-result'));
    if(actual.field.some((z,i)=>z.some((part,k)=>Math.abs(part-expected.field[i][k])>1e-10)))errors.push('M1 S4 complex field mismatch '+gate+' '+pattern);
    if(actual.powers.some((p,i)=>Math.abs(p-expected.powers[i])>1e-10)||actual.bit!==expected.bit||actual.expected!==expected.expected||Math.abs(actual.signed_margin-expected.signed_margin)>1e-10)errors.push('M1 S4 truth/margin mismatch '+gate+' '+pattern);
    logicCases++;
  }
  for(const [gate,result] of Object.entries(logicData.baseline)){
    for(const row of result.rows)await verifyGate(gate,row.pattern,3,0,0,row);
  }
  for(const s of logicData.interactive_perturbations)await verifyGate(s.gate,s.pattern,s.reference_amplitude,s.reference_phase_pi,s.theta1_error_pi,s.row);
  await page.locator('#gate-reset').click();
  const resetCase=JSON.parse(await page.locator('#gate-live').getAttribute('data-result'));
  if(!resetCase.baseline||resetCase.bit!==resetCase.expected)errors.push('M1 S4 reset failed');
  await page.locator('#logic-name').fill('QA learner');
  await page.locator('#logic-coverage').fill('80 cases; x3/x4 still enter the physical circuit.');
  await page.locator('#logic-margins').fill('XOR2 minimum signed margin approximately 0.25.');
  await page.locator('#logic-diagnostic').fill('Fixed baseline remains separate from phase perturbations.');
  await page.locator('#logic-generate').click();
  const logicWorksheetData=JSON.parse(await page.locator('#logic-json').inputValue());
  const logicWorksheet=logicWorksheetData.step==='M1 S4'&&logicWorksheetData.instructor_review==='pending'&&logicWorksheetData.coverage.includes('80 cases');
  if(!logicWorksheet)errors.push('M1 S4 learner worksheet mismatch');
  await page.screenshot({path:'work/m1s4-mobile.png',fullPage:true});
  await page.setViewportSize({width:1440,height:1000});
  await page.goto(pathToFileURL(path.join(root,'course/m1_s4.html')).href);
  await page.screenshot({path:'work/m1s4-top.png'});
  await page.locator('figure').first().screenshot({path:'work/m1s4-figure.png'});
  await page.goto(pathToFileURL(path.join(root,'course/m1_s5.html')).href);
  const handoffSpec=JSON.parse(fs.readFileSync(path.join(root,'pic_spec.json'),'utf8'));
  const handoffPhases=JSON.parse(fs.readFileSync(path.join(root,'phase_settings.json'),'utf8'));
  let handoffCases=0,handoffChannels=0;
  for(const [gate,result] of Object.entries(logicData.baseline)){
    await page.locator('#handoff-function').selectOption(gate);
    for(const row of result.rows){
      await page.locator('#handoff-pattern').selectOption(row.pattern);
      const actual=JSON.parse(await page.locator('#handoff-live').getAttribute('data-result'));
      if(actual.field.some((z,i)=>z.some((v,k)=>Math.abs(v-row.field[i][k])>1e-10))||actual.powers.some((p,i)=>Math.abs(p-row.powers[i])>1e-10)||actual.bit!==row.bit||Math.abs(actual.delta-row.delta)>1e-10)errors.push('M1 S5 phase consumer mismatch '+gate+' '+row.pattern);
      handoffCases++;
    }
    for(const [index,channel] of handoffSpec.phase_vector_order.entries()){
      await page.locator('#handoff-channel').selectOption(channel);
      const actual=JSON.parse(await page.locator('#handoff-live').getAttribute('data-result'));
      const expected=handoffSpec.phase_channels.find(c=>c.id===channel);
      const phase=handoffPhases.programs[gate][handoffPhases.channel_order.indexOf(channel)];
      if(actual.vector_index!==index||actual.channel.instance!==expected.instance||actual.channel.location!==expected.location||actual.channel.pad_id!==null||actual.channel.calibration!==null||Math.abs(actual.phase_rad-phase)>1e-12)errors.push('M1 S5 named channel mismatch '+gate+' '+channel);
      handoffChannels++;
    }
  }
  await page.locator('#handoff-name').fill('QA learner');
  await page.locator('#handoff-mapping').fill('14 named phase channels; PAD and calibration pending M2.');
  await page.locator('#handoff-replay').fill('Independent 80/80 replay using bundled model.');
  await page.locator('#handoff-todo').fill('Boundary, PDK, physical I/O, heater/PAD, DRC and connectivity.');
  await page.locator('#handoff-generate').click();
  const handoffNotes=JSON.parse(await page.locator('#handoff-json').inputValue());
  const handoffWorksheet=handoffNotes.step==='M1 S5'&&handoffNotes.instructor_review==='pending'&&handoffNotes.independent_replay.includes('80/80');
  if(!handoffWorksheet)errors.push('M1 S5 learner worksheet mismatch');
  await page.setViewportSize({width:390,height:844});await page.screenshot({path:'work/m1s5-mobile.png',fullPage:true});
  await page.setViewportSize({width:1440,height:1000});await page.goto(pathToFileURL(path.join(root,'course/m1_s5.html')).href);
  await page.screenshot({path:'work/m1s5-top.png'});await page.locator('figure').first().screenshot({path:'work/m1s5-flow.png'});
  await page.goto(pathToFileURL(path.join(root,'course/m2_s1.html')).href);
  const boundaryData=JSON.parse(fs.readFileSync(path.join(root,'work/m2_s1/out/boundary_results.json'),'utf8'));
  const boundaryPlan=boundaryData.plan;
  let boundaryBlockCases=0,boundaryInterfaceCases=0;
  for(const block of boundaryPlan.system_blocks){
    await page.locator('#boundary-block').selectOption(block.id);
    const live=JSON.parse(await page.locator('#boundary-live').getAttribute('data-result'));
    if(live.block_id!==block.id||live.block_domain!==block.domain)errors.push('M2 S1 block location mismatch '+block.id);
    boundaryBlockCases++;
  }
  for(const gate of Object.keys(handoffPhases.programs)){
    await page.locator('#boundary-gate').selectOption(gate);
    for(const row of [...boundaryPlan.optical_io,...boundaryPlan.electrical_io]){
      await page.locator('#boundary-interface').selectOption(row.interface_id);
      const live=JSON.parse(await page.locator('#boundary-live').getAttribute('data-result'));
      if(JSON.stringify(live.path)!==JSON.stringify(boundaryData.traces[row.interface_id]))errors.push('M2 S1 endpoint path mismatch '+row.interface_id);
      const phaseChannel=row.phase_channel||null;
      const phase=phaseChannel===null?null:handoffPhases.programs[gate][handoffPhases.channel_order.indexOf(phaseChannel)];
      if(live.phase_channel!==phaseChannel||live.physical_pad_count!==null||(phase===null?live.phase_rad!==null:Math.abs(live.phase_rad-phase)>1e-12))errors.push('M2 S1 phase/physical assignment mismatch '+row.interface_id);
      boundaryInterfaceCases++;
    }
  }
  await page.locator('#boundary-name').fill('QA learner');
  await page.locator('#boundary-scope').fill('Laser, data modulation and receiver external; B7 and interfaces planned on PIC.');
  await page.locator('#boundary-paths').fill('CTRL_phi7 to heater A/B to logical GND and DRV_RETURN.');
  await page.locator('#boundary-pending').fill('PAD count, calibration, coupling and receiver gains pending.');
  await page.locator('#boundary-generate').click();
  const boundaryNotes=JSON.parse(await page.locator('#boundary-json').inputValue());
  const boundaryWorksheet=boundaryNotes.step==='M2 S1'&&boundaryNotes.instructor_review==='pending'&&boundaryNotes.interface_paths.includes('CTRL_phi7');
  if(!boundaryWorksheet)errors.push('M2 S1 learner worksheet mismatch');
  await page.setViewportSize({width:390,height:844});await page.screenshot({path:'work/m2s1-mobile.png',fullPage:true});
  await page.setViewportSize({width:1440,height:1000});await page.goto(pathToFileURL(path.join(root,'course/m2_s1.html')).href);
  await page.screenshot({path:'work/m2s1-top.png'});
  await page.locator('figure').nth(0).screenshot({path:'work/m2s1-boundary.png'});
  await page.locator('figure').nth(1).screenshot({path:'work/m2s1-loop.png'});

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

  const result={m2_s2_cases:pdkCaseCount,m2_s2_worksheet:pdkWorksheet,status:errors.length?'failed':'passed',engine:'Google Chrome / Playwright, headless',checks:checked,
    interactive_cases:5,m0_s3_interactive_cases:7,m1_s1_interactive_cases:logicSamples.length,m1_s1_worksheet:m1worksheet,m1_s2_interactive_cases:b7Samples.length,m1_s2_worksheet:b7worksheet,m1_s2_reference_check:true,m1_s3_interactive_cases:readSamples.length,m1_s3_worksheet:readWorksheet,m1_s3_exact_boundary:exactBoundary.bit===null,m1_s4_interactive_cases:logicCases,m1_s4_worksheet:logicWorksheet,m1_s4_reset:resetCase.baseline,m1_s5_consumer_cases:handoffCases,m1_s5_channel_cases:handoffChannels,m1_s5_worksheet:handoffWorksheet,m2_s1_block_cases:boundaryBlockCases,m2_s1_interface_cases:boundaryInterfaceCases,m2_s1_worksheet:boundaryWorksheet,learner_json_generation:data.step==='M0 S1',errors};
  fs.writeFileSync(path.join(root,'evidence/browser_checks.json'),JSON.stringify(result,null,2));
  console.log(JSON.stringify(result,null,2));
  await browser.close();if(errors.length)process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1;});
