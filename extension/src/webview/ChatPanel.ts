import * as http from 'http';
import * as vscode from 'vscode';
import { getHtmlContent } from './chatHtml';
import { ApiClient, ChatResponse, defaultClient } from '../client/ApiClient';
import { CommandExecutor } from '../executor/CommandExecutor';

export class ChatPanel {
    private static _panel: vscode.WebviewPanel | undefined;
    private readonly _client: ApiClient;
    private readonly _executor: CommandExecutor;
    private readonly _webviewPanel: vscode.WebviewPanel;

    constructor(panel: vscode.WebviewPanel, client: ApiClient = defaultClient) {
        this._webviewPanel = panel;
        this._client = client;
        this._executor = new CommandExecutor(
            async (cmd: string) => { await vscode.commands.executeCommand(cmd); },
            async (msg: string) => {
                const result = await vscode.window.showWarningMessage(msg, '确认', '取消');
                return result === '确认';
            }
        );

        this._webviewPanel.webview.onDidReceiveMessage(async (data: { type: string; message: string }) => {
            if (data.type === 'chat') {
                try {
                    const response = await this._client.sendMessage(data.message, 'chat-session');
                    await this._webviewPanel.webview.postMessage(response);
                    await this._executor.handle(response);
                } catch (err) {
                    await this._webviewPanel.webview.postMessage({
                        type: 'error',
                        message: err instanceof Error ? err.message : String(err)
                    });
                }
            } else if (data.type === 'stream') {
                this.sendMessageStream(data.message, 'chat-session');
            }
        });

        this._webviewPanel.onDidDispose(() => {
            ChatPanel._panel = undefined;
        });
    }

    sendMessageStream(message: string, threadId: string): void {
        void this._webviewPanel.webview.postMessage({ type: 'statusUpdate', text: '正在识别意图...' });

        const url = new URL(this._client.buildUrl('/chat/stream'));
        const body = JSON.stringify({ message, thread_id: threadId });
        const options: http.RequestOptions = {
            hostname: url.hostname,
            port: parseInt(url.port || '80'),
            path: url.pathname,
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(body),
            },
        };

        const req = http.request(options, (res) => {
            let buffer = '';
            res.setEncoding('utf8');
            res.on('data', (chunk: string) => {
                buffer += chunk;
                const lines = buffer.split('\n');
                buffer = lines.pop() ?? '';
                for (const line of lines) {
                    if (!line.startsWith('data: ')) { continue; }
                    const payload = line.slice(6);
                    if (payload === '[DONE]') {
                        void this._webviewPanel.webview.postMessage({ type: 'streamDone' });
                        return;
                    }
                    try {
                        const event = JSON.parse(payload) as Record<string, unknown>;
                        if (event['type'] === 'action') {
                            const description = (event['description'] as string) ?? '';
                            void this._webviewPanel.webview.postMessage({
                                type: 'statusUpdate',
                                text: `执行中：${description}`,
                            });
                            this._executor.handle(event as unknown as ChatResponse).finally(() => {
                                void this._webviewPanel.webview.postMessage({
                                    type: 'actionDone',
                                    description,
                                });
                            });
                        } else if (event['delta'] !== undefined) {
                            void this._webviewPanel.webview.postMessage({
                                type: 'streamChunk',
                                delta: event['delta'] as string,
                            });
                        }
                    } catch { /* ignore JSON parse errors */ }
                }
            });
        });

        req.on('error', (err: Error) => {
            void this._webviewPanel.webview.postMessage({
                type: 'error',
                message: err.message,
            });
        });

        req.write(body);
        req.end();
    }

    static createOrShow(extensionUri: vscode.Uri): void {
        const column = vscode.window.activeTextEditor?.viewColumn;

        if (ChatPanel._panel) {
            ChatPanel._panel.reveal(column);
            return;
        }

        const panel = vscode.window.createWebviewPanel(
            'hisparkAiChat',
            'HiSpark AI Chat',
            column || vscode.ViewColumn.One,
            { enableScripts: true }
        );
        panel.webview.html = getHtmlContent();
        ChatPanel._panel = panel;
        new ChatPanel(panel);
        // suppress unused extensionUri warning — may be used for local resources in future versions
        void extensionUri;
    }
}
