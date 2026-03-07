import * as fs from 'fs';
import * as vscode from 'vscode';
import { ApiClient } from '../../client/ApiClient';
import { ChatPanel } from '../../webview/ChatPanel';
import { getHtmlContent } from '../../webview/chatHtml';

/** Minimal test runner used by Phase 2 of runTests.ts.
 *
 *  Creates the chat panel with the E2E backend port injected via DI,
 *  then polls E2E_SIGNAL_FILE until runTests.ts signals completion. */
export async function run(): Promise<void> {
    const backendPort = process.env.HISPARK_TEST_BACKEND_PORT ?? '8001';
    const client = new ApiClient(`http://127.0.0.1:${backendPort}`);

    const panel = vscode.window.createWebviewPanel(
        'hisparkAiChat',
        'HiSpark AI Chat',
        vscode.ViewColumn.One,
        { enableScripts: true }
    );
    panel.webview.html = getHtmlContent();
    new ChatPanel(panel, client);  // DI: inject test backend client

    const signalFile = process.env.E2E_SIGNAL_FILE;
    const mode = process.env.E2E_MODE ?? 'manual';
    const failDelay = mode === 'gate' ? 0 : 5000;

    // Clean up stale signal from a previous run
    if (signalFile && fs.existsSync(signalFile)) { fs.unlinkSync(signalFile); }

    await new Promise<void>((resolve) => {
        // Safety timeout: 90 seconds in case signal is never written
        const safetyTimer = setTimeout(resolve, 90_000);

        const iv = setInterval(() => {
            if (!signalFile || !fs.existsSync(signalFile)) { return; }

            clearInterval(iv);
            clearTimeout(safetyTimer);

            const result = fs.readFileSync(signalFile, 'utf-8');
            if (result === 'fail' && failDelay > 0) {
                console.log(`[E2E] Test failed. Keeping VS Code open for ${failDelay / 1000}s (manual mode)...`);
                setTimeout(resolve, failDelay);
            } else {
                resolve();
            }
        }, 500);
    });
}
