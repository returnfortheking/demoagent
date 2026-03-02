import * as vscode from 'vscode';
import { ChatPanel } from './webview/ChatPanel';

export function activate(context: vscode.ExtensionContext): void {
    const disposable = vscode.commands.registerCommand(
        'hispark-ai-agent.openChat',
        () => ChatPanel.createOrShow(context.extensionUri)
    );
    context.subscriptions.push(disposable);
}

export function deactivate(): void {}
