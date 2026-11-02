const {chromium}=require('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1029-1117-0_26.1029.1117.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules/playwright');
const path=require('path');const {pathToFileURL}=require('url');
(async()=>{const browser=await chromium.launchPersistentContext(path.resolve('work/browser-profile-final'),{headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});const page=await browser.newPage({viewport:{width:1440,height:1000}});
await page.goto(pathToFileURL('C:/EDA_Codex/Lab06b/course/m2_s7.html').href);await page.locator('figure').nth(3).screenshot({path:'work/m2s7-sensitivity.png'});
await page.goto(pathToFileURL('C:/EDA_Codex/Lab06b/Lab06b_index.html').href);await page.screenshot({path:'work/m2s7-home.png'});
if(!await page.locator('main').innerText().then(t=>t.includes('M2 S7 教學交付包與搬移重播通過')&&t.includes('下一步 M3 S1')))throw Error('Home progress mismatch');
await browser.close();console.log('Final chart and home progress checked');})().catch(e=>{console.error(e);process.exitCode=1;});
