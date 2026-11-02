const {chromium} = require('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1029-1117-0_26.1029.1117.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules/playwright');
const fs = require('fs');
const path = require('path');
const {pathToFileURL} = require('url');
const root = path.resolve(process.argv[2] || 'outputs/Lab06b');
(async()=>{
  const browser=await chromium.launchPersistentContext(path.resolve('work/browser-profile-m2s7'),{headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--disable-crash-reporter']});
  const page=await browser.newPage({viewport:{width:1440,height:1000},deviceScaleFactor:1});
  const errors=[];page.on('pageerror',e=>errors.push(String(e)));
  const checked=[];
  for(const file of ['Lab06b_index.html','course/plan.html','course/m0_s1.html','course/m0_s2.html','course/m0_s3.html','course/m1_s1.html','course/m1_s2.html','course/m1_s3.html','course/m1_s4.html','course/m1_s5.html','course/m2_s1.html','course/m2_s2.html','course/m2_s3.html','course/m2_s4.html','course/m2_s5.html','course/m2_s6.html','course/m2_s7.html','course/m0_s1_foundation.html','analysis/lab01a_7_6.html','reference/source_context.html','reference/C01/reader.html']){
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
  for(const file of ['Lab06b_index.html','course/plan.html','course/m0_s1.html','course/m0_s2.html','course/m0_s3.html','course/m1_s1.html','course/m1_s2.html','course/m1_s3.html','course/m1_s4.html','course/m1_s5.html','course/m2_s1.html','course/m2_s2.html','course/m2_s3.html','course/m2_s4.html','course/m2_s5.html','course/m2_s6.html','course/m2_s7.html','course/m0_s1_foundation.html','analysis/lab01a_7_6.html']){
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

  const result={m2_s7_replay_cases:deliveryCases,m2_s7_path_cases:deliveryPathCases,m2_s7_worksheet:deliveryWorksheet,m2_s6_route_cases:verifyRouteCases,m2_s6_control_cases:verifyControlCases,m2_s6_worksheet:verifyWorksheet,m2_s5_pad_cases:chipPadCases,m2_s5_optical_cases:chipOpticalCases,m2_s5_worksheet:chipWorksheet,m2_s4_cases:reviewCases,m2_s4_worksheet:reviewWorksheet,m2_s3_cases:layoutCases,m2_s3_worksheet:layoutWorksheet,m2_s2_cases:pdkCaseCount,m2_s2_worksheet:pdkWorksheet,status:errors.length?'failed':'passed',engine:'Google Chrome / Playwright, headless',checks:checked,
    interactive_cases:5,m0_s3_interactive_cases:7,m1_s1_interactive_cases:logicSamples.length,m1_s1_worksheet:m1worksheet,m1_s2_interactive_cases:b7Samples.length,m1_s2_worksheet:b7worksheet,m1_s2_reference_check:true,m1_s3_interactive_cases:readSamples.length,m1_s3_worksheet:readWorksheet,m1_s3_exact_boundary:exactBoundary.bit===null,m1_s4_interactive_cases:logicCases,m1_s4_worksheet:logicWorksheet,m1_s4_reset:resetCase.baseline,m1_s5_consumer_cases:handoffCases,m1_s5_channel_cases:handoffChannels,m1_s5_worksheet:handoffWorksheet,m2_s1_block_cases:boundaryBlockCases,m2_s1_interface_cases:boundaryInterfaceCases,m2_s1_worksheet:boundaryWorksheet,learner_json_generation:data.step==='M0 S1',errors};
  fs.writeFileSync(path.join(root,'evidence/browser_checks.json'),JSON.stringify(result,null,2));
  console.log(JSON.stringify(result,null,2));
  await browser.close();if(errors.length)process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1;});
