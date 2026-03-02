import * as path from 'path';
import Mocha from 'mocha';

export function run(): Promise<void> {
    const mocha = new Mocha({ ui: 'tdd', color: true, timeout: 5000 });
    const testDir = path.resolve(__dirname);
    return new Promise((resolve, reject) => {
        mocha.addFile(path.join(testDir, 'apiClient.test.js'));
        mocha.addFile(path.join(testDir, 'commandExecutor.test.js'));
        mocha.run(failures => {
            if (failures > 0) {
                reject(new Error(`${failures} test(s) failed`));
            } else {
                resolve();
            }
        });
    });
}
