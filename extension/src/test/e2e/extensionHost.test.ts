import * as assert from 'assert';
import * as vscode from 'vscode';
import { ApiClient } from '../../client/ApiClient';
import { ChatPanel } from '../../webview/ChatPanel';

const BACKEND_PORT = process.env.HISPARK_TEST_BACKEND_PORT ?? '8001';
const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}`;

suite('E2E: Extension + Backend', () => {
    test('ApiClient: build intent returns action response', async () => {
        const client = new ApiClient(BACKEND_URL);
        const response = await client.sendMessage('帮我编译项目', 'e2e-ts-test');
        assert.strictEqual(response.type, 'action');
        assert.strictEqual(response.command, 'hispark-studio.build');
    });

    test('Extension activates and openChat command executes without error', async () => {
        await assert.doesNotReject(
            () => Promise.resolve(vscode.commands.executeCommand('hispark-ai-agent.openChat'))
        );
    });

    test('ChatPanel: accepts injected ApiClient via constructor DI', () => {
        const panel = vscode.window.createWebviewPanel(
            'testChat', 'Test Chat', vscode.ViewColumn.One,
            { enableScripts: true }
        );
        const client = new ApiClient(BACKEND_URL);
        const chatPanel = new ChatPanel(panel, client);
        assert.ok(chatPanel, 'ChatPanel should be constructable with injected client');
        panel.dispose();
    });
});
