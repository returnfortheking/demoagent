import * as assert from 'assert';
import { getHtmlContent } from '../../webview/chatHtml';

suite('ChatPanel', () => {
    test('HTML structure completeness', () => {
        const html = getHtmlContent();
        assert.ok(html.includes('<!DOCTYPE html>'), 'Should contain <!DOCTYPE html>');
        assert.ok(/<input[\s>]/i.test(html), 'Should contain an <input> element');
        assert.ok(/<button[\s>]/i.test(html), 'Should contain a <button> element');
    });

    test('No external scripts or resources', () => {
        const html = getHtmlContent();
        assert.ok(html.includes('Content-Security-Policy'), 'Should have CSP meta tag');
        // Check that no src or href attributes reference external http/https URLs
        const srcMatches = html.match(/src\s*=\s*["'][^"']*["']/gi) || [];
        const hrefMatches = html.match(/href\s*=\s*["'][^"']*["']/gi) || [];
        const allAttributes = [...srcMatches, ...hrefMatches];
        for (const attr of allAttributes) {
            assert.ok(
                !attr.includes('http://') && !attr.includes('https://'),
                `External URL found in attribute: ${attr}`
            );
        }
    });

    test('postMessage call exists', () => {
        const html = getHtmlContent();
        assert.ok(html.includes('acquireVsCodeApi'), 'Should contain acquireVsCodeApi call');
        assert.ok(html.includes('vscode.postMessage'), 'Should contain vscode.postMessage call');
    });
});
