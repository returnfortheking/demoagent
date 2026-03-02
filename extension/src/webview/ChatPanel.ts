import * as vscode from 'vscode';
import { getHtmlContent } from './chatHtml';
import { defaultClient } from '../client/ApiClient';
import { CommandExecutor } from '../executor/CommandExecutor';

export class ChatPanel {
    private static _panel: vscode.WebviewPanel | undefined;
    private readonly _executor: CommandExecutor;
    private readonly _webviewPanel: vscode.WebviewPanel;

    constructor(panel: vscode.WebviewPanel) {
        this._webviewPanel = panel;
        this._executor = new CommandExecutor(
            async (cmd: string) => { await vscode.commands.executeCommand(cmd); },
            async (msg: string) => {
                const result = await vscode.window.showWarningMessage(msg, '确认', '取消');
                return result === '确认';
            }
        );

        this._webviewPanel.webview.onDidReceiveMessage(async (data: { type: string; message: string }) => {
            if (data.type !== 'chat') { return; }
            try {
                const response = await defaultClient.sendMessage(data.message, 'chat-session');
                await this._webviewPanel.webview.postMessage(response);
                await this._executor.handle(response);
            } catch (err) {
                await this._webviewPanel.webview.postMessage({
                    type: 'error',
                    message: err instanceof Error ? err.message : String(err)
                });
            }
        });

        this._webviewPanel.onDidDispose(() => {
            ChatPanel._panel = undefined;
        });
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
