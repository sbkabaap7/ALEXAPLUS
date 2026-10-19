import {defineConfig} from '@playwright/test';
import {resolve} from 'node:path';
export default defineConfig({testDir:'./e2e',fullyParallel:false,workers:1,timeout:60000,use:{baseURL:'http://127.0.0.1:8877',trace:'retain-on-failure',launchOptions:{args:['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream',`--use-file-for-fake-audio-capture=${resolve('../models/test-fixtures/example1.wav')}`]}},projects:[{name:'chromium',use:{browserName:'chromium'}}]});
