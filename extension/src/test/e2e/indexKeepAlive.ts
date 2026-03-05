import * as vscode from 'vscode';
import { ApiClient } from '../../client/ApiClient';
import { ChatPanel } from '../../webview/ChatPanel';
import { getHtmlContent } from '../../webview/chatHtml';

/** Minimal test runner used by Phase 2 of runTests.ts.
 *
 *  Creates the chat panel with the E2E backend port injected via DI
 *  (not via openChat command which would use defaultClient on port 8000),
 *  then keeps VS Code alive for 45 seconds while Playwright runs its tests. */
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

    // Keep VS Code alive for Playwright tests to run
    await new Promise(r => setTimeout(r, 45000));
}
