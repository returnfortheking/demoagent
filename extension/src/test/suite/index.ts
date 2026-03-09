import * as path from 'path';
import Mocha from 'mocha';

export function run(): Promise<void> {
    const mocha = new Mocha({ ui: 'tdd', color: true, timeout: 5000 });
    const testDir = path.resolve(__dirname);
    return new Promise((resolve, reject) => {
        mocha.addFile(path.join(testDir, 'apiClient.test.js'));
        mocha.addFile(path.join(testDir, 'commandExecutor.test.js'));
        mocha.addFile(path.join(testDir, 'chatPanel.test.js'));
        mocha.addFile(path.join(testDir, 'streaming.test.js'));
        mocha.run(failures => {
            if (failures > 0) {
                reject(new Error(`${failures} test(s) failed`));
            } else {
                resolve();
            }
        });
    });
}

// Bootstrap: invoke run() when executed directly with node
if (require.main === module) {
    run().catch(err => {
        console.error(err);
        process.exit(1);
    });
}
