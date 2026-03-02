import * as assert from 'assert';
import { CommandExecutor } from '../../executor/CommandExecutor';
import { ChatResponse } from '../../client/ApiClient';

suite('CommandExecutor', () => {
    test('Normal command executes directly without confirmation', async () => {
        const executedCommands: string[] = [];
        const confirmMessages: string[] = [];

        const mockExecute = async (cmd: string) => { executedCommands.push(cmd); };
        const mockConfirm = async (msg: string) => { confirmMessages.push(msg); return true; };

        const executor = new CommandExecutor(mockExecute, mockConfirm);
        const response: ChatResponse = {
            type: 'action',
            command: 'hispark-studio.build',
            requires_confirmation: false,
            description: '编译'
        };

        await executor.handle(response);

        assert.strictEqual(executedCommands.length, 1, 'executeFn should be called once');
        assert.strictEqual(executedCommands[0], 'hispark-studio.build');
        assert.strictEqual(confirmMessages.length, 0, 'confirmFn should not be called');
    });

    test('Dangerous command executes when user confirms', async () => {
        const executedCommands: string[] = [];
        const confirmMessages: string[] = [];

        const mockExecute = async (cmd: string) => { executedCommands.push(cmd); };
        const mockConfirm = async (msg: string) => { confirmMessages.push(msg); return true; };

        const executor = new CommandExecutor(mockExecute, mockConfirm);
        const response: ChatResponse = {
            type: 'action',
            command: 'hispark-studio.flash',
            requires_confirmation: true,
            description: '烧录固件'
        };

        await executor.handle(response);

        assert.strictEqual(executedCommands.length, 1, 'executeFn should be called once');
        assert.strictEqual(executedCommands[0], 'hispark-studio.flash');
        assert.strictEqual(confirmMessages.length, 1, 'confirmFn should be called once');
    });

    test('Dangerous command is cancelled when user declines', async () => {
        const executedCommands: string[] = [];
        const confirmMessages: string[] = [];

        const mockExecute = async (cmd: string) => { executedCommands.push(cmd); };
        const mockConfirm = async (msg: string) => { confirmMessages.push(msg); return false; };

        const executor = new CommandExecutor(mockExecute, mockConfirm);
        const response: ChatResponse = {
            type: 'action',
            command: 'hispark-studio.flash',
            requires_confirmation: true,
            description: '烧录固件'
        };

        await executor.handle(response);

        assert.strictEqual(executedCommands.length, 0, 'executeFn should not be called');
        assert.strictEqual(confirmMessages.length, 1, 'confirmFn should be called once');
    });

    test('Answer type response is ignored', async () => {
        const executedCommands: string[] = [];
        const confirmMessages: string[] = [];

        const mockExecute = async (cmd: string) => { executedCommands.push(cmd); };
        const mockConfirm = async (msg: string) => { confirmMessages.push(msg); return true; };

        const executor = new CommandExecutor(mockExecute, mockConfirm);
        const response: ChatResponse = {
            type: 'answer',
            answer: 'Here is your answer'
        };

        await executor.handle(response);

        assert.strictEqual(executedCommands.length, 0, 'executeFn should not be called');
        assert.strictEqual(confirmMessages.length, 0, 'confirmFn should not be called');
    });

    test('Flash confirmation message contains description', async () => {
        const confirmMessages: string[] = [];

        const mockExecute = async (_cmd: string) => {};
        const mockConfirm = async (msg: string) => { confirmMessages.push(msg); return true; };

        const executor = new CommandExecutor(mockExecute, mockConfirm);
        const response: ChatResponse = {
            type: 'action',
            command: 'hispark-studio.flash',
            requires_confirmation: true,
            description: '烧录固件'
        };

        await executor.handle(response);

        assert.strictEqual(confirmMessages.length, 1, 'confirmFn should be called once');
        assert.ok(
            confirmMessages[0].includes('烧录固件'),
            `Confirmation message should contain description '烧录固件', got: "${confirmMessages[0]}"`
        );
    });
});
