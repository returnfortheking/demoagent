import * as path from 'path';
import * as fs from 'fs';
import Mocha from 'mocha';

export async function run(): Promise<void> {
    const mocha = new Mocha({ ui: 'tdd', color: true, timeout: 30000 });

    const testFiles = fs.readdirSync(__dirname).filter(f => f.endsWith('.test.js'));
    testFiles.forEach(f => mocha.addFile(path.resolve(__dirname, f)));

    return new Promise((resolve, reject) => {
        mocha.run(failures => {
            if (failures > 0) {
                reject(new Error(`${failures} E2E test(s) failed`));
            } else {
                resolve();
            }
        });
    });
}
