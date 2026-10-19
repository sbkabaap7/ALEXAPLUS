// Own exact child PIDs rather than Playwright's cmd.exe process-tree cleanup on Windows.
import {spawn} from 'node:child_process';
import {resolve} from 'node:path';
import {mkdtemp} from 'node:fs/promises';
import {tmpdir} from 'node:os';
const root=resolve('..');
const data=await mkdtemp(resolve(tmpdir(),'guestguard-e2e-'));
const python=resolve(root,process.platform==='win32'?'.venv/Scripts/python.exe':'.venv/bin/python');
const server=spawn(python,['-m','uvicorn','backend.app.main:app','--host','127.0.0.1','--port','8877','--no-access-log'],{cwd:root,env:{...process.env,GUESTGUARD_DATA_DIR:data,GUESTGUARD_BASE_URL:'http://127.0.0.1:8877',GUESTGUARD_OLLAMA_MODEL:'guestguard-e2e-model-not-installed'},stdio:['ignore','ignore','pipe'],windowsHide:true});
let actualPid;
server.stderr.on('data',chunk=>{const match=chunk.toString().match(/Started server process \[(\d+)\]/);if(match)actualPid=Number(match[1]);});
function stop(){for(const pid of new Set([actualPid,server.pid].filter(Boolean))){try{process.kill(pid);}catch{}}}
process.on('exit',stop);process.on('SIGINT',()=>{stop();process.exit(130);});
try{
 let ready=false;
 for(let i=0;i<100;i++){try{const response=await fetch('http://127.0.0.1:8877/api/health');if(response.ok){ready=true;break;}}catch{}await new Promise(r=>setTimeout(r,100));}
 if(!ready)throw new Error('Isolated E2E server did not become ready');
 const test=spawn(process.execPath,['node_modules/@playwright/test/cli.js','test','--reporter=line','--global-timeout=90000',...process.argv.slice(2)],{cwd:process.cwd(),stdio:'inherit',windowsHide:true});
 const code=await new Promise((resolve,reject)=>{test.once('exit',resolve);test.once('error',reject);});
 stop();process.exitCode=code??1;
}catch(error){stop();console.error(error.message);process.exitCode=1;}
