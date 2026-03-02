import * as vscode from 'vscode';

export function activate(context: vscode.ExtensionContext): void {
    const disposable = vscode.commands.registerCommand(
        'hispark-ai-agent.openChat',
        () => {
            vscode.window.showInformationMessage('HiSpark AI Chat - Coming soon!');
        }
    );
    context.subscriptions.push(disposable);
}

export function deactivate(): void {}
