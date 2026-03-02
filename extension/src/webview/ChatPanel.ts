import * as vscode from 'vscode';
import { getHtmlContent } from './chatHtml';

export class ChatPanel {
    private static _panel: vscode.WebviewPanel | undefined;

    static createOrShow(extensionUri: vscode.Uri): void {
        const column = vscode.window.activeTextEditor
            ? vscode.window.activeTextEditor.viewColumn
            : undefined;

        if (ChatPanel._panel) {
            ChatPanel._panel.reveal(column);
            return;
        }

        ChatPanel._panel = vscode.window.createWebviewPanel(
            'hisparkAiChat',
            'HiSpark AI Chat',
            column || vscode.ViewColumn.One,
            { enableScripts: true }
        );
        ChatPanel._panel.webview.html = getHtmlContent();
        ChatPanel._panel.onDidDispose(() => {
            ChatPanel._panel = undefined;
        });
    }
}
