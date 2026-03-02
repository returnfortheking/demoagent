import * as assert from 'assert';
import { ApiClient } from '../../client/ApiClient';

suite('ApiClient', () => {
    test('buildUrl concatenates baseUrl and path correctly', () => {
        const client = new ApiClient('http://localhost:8000');
        const result = client.buildUrl('/chat');
        assert.strictEqual(result, 'http://localhost:8000/chat');
    });

    test('buildUrl avoids double slash when baseUrl has trailing slash', () => {
        const client = new ApiClient('http://localhost:8000/');
        const result = client.buildUrl('/chat');
        assert.strictEqual(result, 'http://localhost:8000/chat');
    });

    test('parseResponse handles action type response', () => {
        const client = new ApiClient('http://localhost:8000');
        const raw = {
            type: 'action',
            command: 'hispark-studio.build',
            requires_confirmation: false,
            description: '编译',
            args: {}
        };
        const response = client.parseResponse(raw);
        assert.strictEqual(response.type, 'action');
        assert.strictEqual(response.command, 'hispark-studio.build');
        assert.strictEqual(response.requires_confirmation, false);
    });

    test('parseResponse handles answer type response', () => {
        const client = new ApiClient('http://localhost:8000');
        const raw = {
            type: 'answer',
            answer: 'some answer'
        };
        const response = client.parseResponse(raw);
        assert.strictEqual(response.type, 'answer');
        assert.ok(response.answer, 'answer field should have a value');
    });
});
