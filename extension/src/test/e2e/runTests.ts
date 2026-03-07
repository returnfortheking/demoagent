import * as path from 'path';
import * as cp from 'child_process';
import * as fs from 'fs';
import * as http from 'http';
import * as os from 'os';
import { runTests } from '@vscode/test-electron';
import { runWebviewTests } from './webview.playwright';

const BACKEND_PORT = 8001;
const CDP_PORT = 9222;

function waitForHealth(url: string, maxAttempts = 30): Promise<void> {
    return new Promise((resolve, reject) => {
        let attempts = 0;
        const check = () => {
            attempts++;
            const req = http.get(url, (res) => {
                res.resume();
                if (res.statusCode === 200) {
                    resolve();
                } else if (attempts < maxAttempts) {
                    setTimeout(check, 1000);
                } else {
                    reject(new Error(`Backend health check failed after ${maxAttempts} attempts`));
                }
            });
            req.on('error', () => {
                if (attempts < maxAttempts) {
                    setTimeout(check, 1000);
                } else {
                    reject(new Error(`Backend did not start within ${maxAttempts} seconds`));
                }
            });
        };
        check();
    });
}

async function main(): Promise<void> {
    // Paths relative to compiled output: out/test/e2e/runTests.js
    const extensionDevelopmentPath = path.resolve(__dirname, '../../..');
    const backendDir = path.resolve(__dirname, '../../../../backend');

    const python = process.env.PYTHON_PATH ?? 'python';
    console.log(`[E2E] Starting backend (port ${BACKEND_PORT}) via ${python} ...`);

    const backend = cp.spawn(
        python,
        ['-m', 'uvicorn', 'src.api.main:app', '--host', '127.0.0.1', '--port', String(BACKEND_PORT)],
        { cwd: backendDir, env: process.env, stdio: 'inherit' }
    );

    backend.on('error', (err) => {
        console.error('[E2E] Failed to start backend:', err.message);
    });

    try {
        await waitForHealth(`http://127.0.0.1:${BACKEND_PORT}/health`);
        console.log(`[E2E] Backend ready on port ${BACKEND_PORT}`);

        // ── Phase 1: Extension host tests (Mocha inside VS Code) ──────────────
        console.log('\n[E2E] Phase 1: Extension host tests');
        await runTests({
            extensionDevelopmentPath,
            extensionTestsPath: path.resolve(__dirname, './index'),
            extensionTestsEnv: {
                HISPARK_TEST_BACKEND_PORT: String(BACKEND_PORT),
            },
        });

        // ── Phase 2: Playwright webview tests (Node.js, outside VS Code) ──────
        console.log('\n[E2E] Phase 2: Playwright webview tests');

        const signalFile = path.join(os.tmpdir(), `e2e-signal-${Date.now()}`);
        const e2eMode = process.env.E2E_MODE ?? 'manual';

        // Start VS Code with the keep-alive runner and CDP port open.
        // indexKeepAlive opens the chat panel, then polls signalFile to know when to exit.
        const keepAliveVsCode = runTests({
            extensionDevelopmentPath,
            extensionTestsPath: path.resolve(__dirname, './indexKeepAlive'),
            extensionTestsEnv: {
                HISPARK_TEST_BACKEND_PORT: String(BACKEND_PORT),
                E2E_SIGNAL_FILE: signalFile,
                E2E_MODE: e2eMode,
            },
            launchArgs: [`--remote-debugging-port=${CDP_PORT}`],
        });

        // Run Playwright from THIS Node.js process (avoids self-referential CDP).
        // The Playwright side handles connection retries, so we avoid hard-coded
        // sleep here which can miss timing windows on fast/slow machines.
        try {
            await runWebviewTests(CDP_PORT);
            fs.writeFileSync(signalFile, 'pass');
        } catch (err) {
            fs.writeFileSync(signalFile, 'fail');
            throw err;
        } finally {
            // Always wait for VS Code to close after keep-alive finishes.
            await keepAliveVsCode;
            if (fs.existsSync(signalFile)) { fs.unlinkSync(signalFile); }
        }

    } finally {
        backend.kill();
        console.log('[E2E] Backend process terminated');
    }
}

main().catch((err: unknown) => {
    console.error('[E2E] Fatal error:', err);
    process.exit(1);
});
