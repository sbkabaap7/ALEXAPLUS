import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
import {resolve} from 'node:path';

test('one-screen home answers requests and keeps its video playing',async({page})=>{
 const failures:string[]=[];page.on('pageerror',error=>failures.push(error.message));
 await page.goto('/');
 await expect(page.getByRole('heading',{name:'Ask anything. Check what matters.'})).toBeVisible();
 await expect(page.locator('.scene-video')).toHaveCount(1);
 await expect(page.getByRole('button',{name:'Voice & PIN'})).toBeVisible();
 for(const name of ['Menu','Talk','Activity','Settings','Privacy'])await expect(page.getByRole('button',{name,exact:true})).toHaveCount(0);
 await expect.poll(()=>page.locator('.hero-video').evaluate(video=>!(video as HTMLVideoElement).paused),{timeout:15000}).toBe(true);
 await page.locator('.hero-video').evaluate(video=>(video as HTMLVideoElement).pause());
 await expect.poll(()=>page.locator('.hero-video').evaluate(video=>!(video as HTMLVideoElement).paused),{timeout:15000}).toBe(true);
 expect(await page.locator('.command-input').evaluate(form=>getComputedStyle(form).animationName)).toBe('rgb-border-shift');
 await page.keyboard.press('/');await expect(page.getByLabel('Your request')).toBeFocused();
 await page.getByRole('button',{name:'What’s on my calendar?'}).click();
 await expect(page.locator('.agent-output')).toContainText('Use the mic so I can check your voice');
 await page.getByLabel('Your request').fill('What is the home status?');await page.getByLabel('Your request').press('Enter');
 await expect(page.locator('.agent-output')).toContainText('The demo home is Studio 04.');
 await page.getByLabel('Your request').fill('hello');await page.getByLabel('Your request').press('Enter');
 await expect(page.locator('.agent-output')).toContainText('Hi! What would you like to check');
 await expect(page.getByRole('region',{name:'Recent requests'}).getByRole('button')).toHaveCount(3);
 for(const [width,name] of [[375,'mobile'],[768,'tablet'],[1440,'overview']] as const){
  await page.setViewportSize({width,height:900});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.screenshot({path:'../docs/screenshots/'+name+'.png',fullPage:true,animations:'disabled'});
 }
 expect(failures).toEqual([]);
});

test('mic shows live words, Escape stops it, and reduced motion shows the poster',async({browser})=>{
 const context=await browser.newContext({permissions:['microphone']});const page=await context.newPage();
 await page.goto('/');await page.getByRole('button',{name:'Record voice',exact:true}).click();
 await expect(page.getByRole('button',{name:'Stop recording',exact:true})).toHaveAttribute('aria-pressed','true');
 await expect(page.getByLabel('Your request')).not.toHaveValue('',{timeout:14000});
 await page.emulateMedia({reducedMotion:'reduce'});
 await expect(page.locator('.hero-video')).toHaveJSProperty('paused',true);
 expect(await page.locator('.home-hero').evaluate(el=>getComputedStyle(el).backgroundImage)).toContain('hero-poster');
 await page.keyboard.press('Escape');
 await expect(page.getByRole('button',{name:'Record voice',exact:true})).toBeEnabled({timeout:45000});
 await context.close();
});

test('a silent recording gives a useful reply',async({browser})=>{
 const context=await browser.newContext({permissions:['microphone']});const page=await context.newPage();
 await page.route(/\/api\/voice$/,route=>route.fulfill({json:{
  assessment:{speaker_status:'UNCERTAIN',similarity:null,quality:{duration:3,speech_seconds:0}},
  transcript:{text:'',available:true,message:'No clear words heard. Try again or type your request.'},
  agent:null,state:{}
 }}));
 await page.goto('/');await page.getByRole('button',{name:'Record voice',exact:true}).click();
 await expect(page.getByRole('button',{name:'Stop recording',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Stop recording',exact:true}).click();
 await expect(page.locator('.response-area')).toContainText('No clear words heard. Try again or type your request.');
 await context.close();
});

test('saved voice persists across sessions and restores private access without a PIN',async({page})=>{
 test.setTimeout(180000);
 await page.goto('/');
 await page.getByRole('button',{name:'Voice & PIN'}).click();
 const dialog=page.getByRole('dialog',{name:'Voice & PIN'});
 await expect(dialog).toBeVisible();
 await page.screenshot({path:'../docs/screenshots/voice-pin.png',animations:'disabled'});
 await dialog.getByLabel('Choose a PIN').fill('845276');
 await dialog.getByRole('button',{name:'Save PIN'}).click();
 await expect(dialog.getByText('PIN Saved',{exact:true})).toBeVisible();
 await dialog.getByRole('checkbox',{name:/I agree to save my voice/}).check();
 for(let index=0;index<3;index++)await dialog.getByLabel('Upload WAV sample',{exact:true}).setInputFiles(resolve('../models/test-fixtures/example1.wav'));
 await expect(dialog.getByLabel('3 of 3 voice samples recorded')).toBeVisible();
 await dialog.getByLabel('PIN to save voice').fill('845276');
 await dialog.getByRole('button',{name:'Save voice'}).click();
 await expect(dialog.getByText('Voice Saved',{exact:true})).toBeVisible({timeout:60000});
 await expect(dialog.getByLabel('PIN to save voice')).toHaveCount(0);
 await dialog.getByRole('button',{name:'Close dialog'}).click();
 const sample=await readFile(resolve('../models/test-fixtures/example1.wav'));
 const voice=await page.request.post('/api/voice',{multipart:{audio:{name:'sample.wav',mimeType:'audio/wav',buffer:sample}}});
 expect(voice.ok()).toBe(true);
 const voiceResult=await voice.json();
 expect(voiceResult.assessment.speaker_status).toBe('OWNER_CANDIDATE');
 expect(voiceResult.state.mode).toBe('PRIVATE');
 expect(voiceResult.state.authentication_status).toBe('UNVERIFIED');
 await page.getByLabel('Your request').fill('Read my confidential note');await page.getByLabel('Your request').press('Enter');
 await expect(page.locator('.agent-output')).toContainText('Synthetic confidential record');
 const newSession=await page.request.post('/api/session');
 expect(newSession.ok()).toBe(true);
 const reusedVoice=await page.request.post('/api/voice',{multipart:{audio:{name:'sample.wav',mimeType:'audio/wav',buffer:sample}}});
 expect(reusedVoice.ok()).toBe(true);
 expect((await reusedVoice.json()).state.mode).toBe('PRIVATE');
 await page.getByLabel('Your request').fill('Read my confidential note');await page.getByLabel('Your request').press('Enter');
 await expect(page.locator('.agent-output')).toContainText('Synthetic confidential record');
 const guest=await page.request.post('/api/guest/simulate',{data:{state:'GUEST_DETECTED'}});
 expect(guest.ok()).toBe(true);
 await expect(page.getByText('Synthetic confidential record',{exact:false})).toHaveCount(0,{timeout:10000});
 await page.getByRole('button',{name:'What’s on my calendar?'}).click();
 await expect(page.locator('.agent-output')).toContainText('Ask again using your saved voice');
 const ownerReturns=await page.request.post('/api/voice',{multipart:{audio:{name:'sample.wav',mimeType:'audio/wav',buffer:sample}}});
 expect(ownerReturns.ok()).toBe(true);
 expect((await ownerReturns.json()).state.mode).toBe('PRIVATE');
 await page.getByLabel('Your request').fill('Read my confidential note');await page.getByLabel('Your request').press('Enter');
 await expect(page.locator('.agent-output')).toContainText('Synthetic confidential record');
 await page.getByRole('button',{name:'Voice & PIN'}).click();
 await dialog.getByRole('button',{name:'Delete saved voice'}).click();
 await dialog.getByLabel('PIN to delete voice').fill('000000');
 await dialog.getByRole('button',{name:'Delete voice'}).click();
 await expect(dialog.getByRole('alert')).toContainText('PIN verification failed');
 await expect(dialog.getByText('Voice Saved',{exact:true})).toBeVisible();
 await dialog.getByLabel('PIN to delete voice').fill('845276');
 await dialog.getByRole('button',{name:'Delete voice'}).click();
 await expect(dialog.getByText('Voice Not saved',{exact:true})).toBeVisible();
});
