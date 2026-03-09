import * as assert from 'assert';
import { initialState, applyStreamEvent } from '../../webview/streamingState';

suite('StreamingMessageHandler', () => {
    test('statusUpdate sets statusText immediately, messages unchanged', () => {
        const state = applyStreamEvent(initialState(), { type: 'statusUpdate', text: '正在识别意图...' });
        assert.strictEqual(state.statusText, '正在识别意图...');
        assert.deepStrictEqual(state.messages, []);
    });

    test('streamChunk clears status bar and accumulates into finalized message on streamDone', () => {
        let state = initialState();
        state = applyStreamEvent(state, { type: 'statusUpdate', text: '...' });
        state = applyStreamEvent(state, { type: 'streamChunk', delta: 'Hello' });
        state = applyStreamEvent(state, { type: 'streamChunk', delta: ' world' });
        state = applyStreamEvent(state, { type: 'streamDone' });

        assert.strictEqual(state.statusText, '');
        assert.strictEqual(state.messages.length, 1);
        assert.strictEqual(state.messages[0].text, 'Hello world');
        assert.strictEqual(state.messages[0].finalized, true);
    });

    test('actionDone clears status bar and appends formatted action message', () => {
        let state = initialState();
        state = applyStreamEvent(state, { type: 'statusUpdate', text: '...' });
        state = applyStreamEvent(state, { type: 'actionDone', description: '编译项目' });

        assert.strictEqual(state.statusText, '');
        assert.strictEqual(state.messages.length, 1);
        assert.strictEqual(state.messages[0].text, '已执行：编译项目');
    });

    test('unknown message type leaves state unchanged', () => {
        const state0 = initialState();
        const state1 = applyStreamEvent(state0, { type: 'response', answer: 'ignored' });
        assert.deepStrictEqual(state1, state0);
    });
});
