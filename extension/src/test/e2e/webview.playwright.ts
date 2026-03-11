import * as assert from 'assert';
import { Browser, Frame, chromium, Page } from 'playwright-core';

const MESSAGE = '帮我编译项目';

function sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function dumpFrames(page: Page): string {
    return page.frames()
        .map((frame, index) => `#${index} name="${frame.name()}" url="${frame.url()}"`)
        .join('\n');
}

async function connectToVsCode(cdpPort: number): Promise<Browser> {
    for (let i = 0; i < 20; i++) {
        try {
            return await chromium.connectOverCDP(`http://localhost:${cdpPort}`, { timeout: 3000 });
        } catch {
            await sleep(500);
        }
    }
    throw new Error(`Could not connect to VS Code CDP at port ${cdpPort}`);
}

async function findTargetPage(browser: Browser): Promise<Page> {
    const deadline = Date.now() + 20000;

    while (Date.now() < deadline) {
        const pages = browser.contexts().flatMap(context => context.pages());
        for (const page of pages) {
            try {
                if (await page.locator('iframe.webview').count() > 0) {
                    return page;
                }
            } catch {
                // Ignore transient page/context shutdown while VS Code boots.
            }
        }
        await sleep(300);
    }

    const pages = browser.contexts().flatMap(context => context.pages());
    assert.ok(pages.length > 0, 'No VS Code page found');
    return pages[0];
}

async function findActiveFrameViaCdp(page: Page): Promise<Frame | undefined> {
    const deadline = Date.now() + 20000;

    while (Date.now() < deadline) {
        const childFrames = page.frames().filter(frame => frame !== page.mainFrame());

        // Most stable signal in VS Code webview structure.
        const namedFrame = childFrames.find(frame => frame.name() === 'active-frame');
        if (namedFrame) {
            return namedFrame;
        }

        // Fallback: identify frame by expected DOM.
        for (const frame of childFrames) {
            try {
                const hasInput = await frame.locator('#chat-input').count();
                const hasSendButton = await frame.locator('#send-btn').count();
                if (hasInput > 0 && hasSendButton > 0) {
                    return frame;
                }
            } catch {
                // Some frames can be inaccessible while reloading; keep polling.
            }
        }

        await sleep(300);
    }

    return undefined;
}

export async function runWebviewTests(cdpPort: number): Promise<void> {
    console.log(`[Playwright] Connecting to VS Code CDP at port ${cdpPort}...`);
    const browser = await connectToVsCode(cdpPort);
    console.log('[Playwright] Connected.');

    try {
        const targetPage = await findTargetPage(browser);

        console.log('[Playwright] Waiting for webview iframe...');
        await targetPage.locator('iframe.webview').first().waitFor({ timeout: 20000 });
        const cls = await targetPage.locator('iframe.webview').first().getAttribute('class');
        console.log(`[Playwright] Webview iframe class: "${cls}"`);

        const activeFrame = await findActiveFrameViaCdp(targetPage);
        if (activeFrame) {
            console.log('[Playwright] Using CDP frame access (active-frame).');

            // ── Non-streaming test (v0.1 baseline) ──────────────────────────────
            await activeFrame.locator('#chat-input').fill(MESSAGE, { timeout: 15000 });
            await activeFrame.locator('#send-btn').click({ timeout: 5000 });
            console.log('[Playwright] Message sent. Waiting for backend response (~3-5s)...');

            const responseDiv = activeFrame.locator('#messages div').first();
            await responseDiv.waitFor({ timeout: 20000 });

            const text = await responseDiv.textContent() ?? '';
            assert.ok(text.includes('"type":"action"'), `Expected action response, got: ${text}`);
            assert.ok(text.includes('"command":"hispark-studio.build"'), `Expected build command, got: ${text}`);
            console.log('[Playwright] ✓ Non-streaming test passed: response rendered in DOM');

            // ── Streaming answer test (F19) ──────────────────────────────────────
            const divsBefore1 = await activeFrame.locator('#messages div').count();
            await activeFrame.locator('#chat-input').fill('HiSpark Studio支持哪些芯片型号？', { timeout: 5000 });
            await activeFrame.locator('#stream-btn').click({ timeout: 5000 });
            console.log('[Playwright] Streaming answer: waiting for status bar...');

            // Wait for status bar to show text (classify_intent takes 1-3s)
            const deadline1 = Date.now() + 5000;
            while (Date.now() < deadline1) {
                const sb = await activeFrame.locator('#status-bar').textContent() ?? '';
                if (sb.trim()) { break; }
                await sleep(200);
            }

            // Wait for streaming bubble to appear in #messages
            await activeFrame.locator('#messages div').nth(divsBefore1).waitFor({ timeout: 20000 });

            // Wait for status bar to clear after [DONE] — stream is fully received
            const deadline2 = Date.now() + 20000;
            while (Date.now() < deadline2) {
                const sb = await activeFrame.locator('#status-bar').textContent() ?? '';
                if (!sb.trim()) { break; }
                await sleep(200);
            }

            // Read final text only after streaming has completed
            const streamText = await activeFrame.locator('#messages div').nth(divsBefore1).textContent() ?? '';

            // Content quality (RAG accuracy) is deferred to v0.3 LangSmith eval.
            // Here we only assert that the stream produced a non-trivial response.
            assert.ok(streamText.length > 20, `Stream answer too short (streaming mechanism broken?), got: ${streamText.slice(0, 200)}`);
            console.log('[Playwright] ✓ Streaming answer test passed');

            // ── Streaming action test (F19) ──────────────────────────────────────
            await activeFrame.locator('#chat-input').fill('帮我编译项目', { timeout: 5000 });
            await activeFrame.locator('#stream-btn').click({ timeout: 5000 });
            console.log('[Playwright] Streaming action: waiting for actionDone message...');

            // Wait for "已执行" div to appear in #messages
            const actionMsgLocator = activeFrame.locator('#messages div').filter({ hasText: '已执行' }).first();
            await actionMsgLocator.waitFor({ timeout: 20000 });
            const actionText = await actionMsgLocator.textContent() ?? '';

            assert.ok(actionText.includes('已执行'), `Expected '已执行' in message, got: ${actionText}`);
            assert.ok(
                actionText.includes('编译') || actionText.includes('项目') || actionText.includes('build'),
                `Expected build-related text in action message, got: ${actionText}`
            );
            console.log('[Playwright] ✓ Streaming action test passed');
            return;
        }

        console.log('[Playwright] CDP frame not found, falling back to frameLocator.');
        const webviewFrame = targetPage
            .frameLocator('iframe.webview')
            .frameLocator('#active-frame');

        await webviewFrame.locator('#chat-input').fill(MESSAGE, { timeout: 15000 });
        await webviewFrame.locator('#send-btn').click({ timeout: 5000 });

        const responseDiv = webviewFrame.locator('#messages div').first();
        await responseDiv.waitFor({ timeout: 20000 });
        const text = await responseDiv.textContent() ?? '';

        assert.ok(text.includes('"type":"action"'), `Expected action response, got: ${text}`);
        assert.ok(text.includes('"command":"hispark-studio.build"'), `Expected build command, got: ${text}`);
        console.log('[Playwright] ✓ Webview test passed: response rendered in DOM (frameLocator fallback)');
    } catch (error) {
        const pages = browser.contexts().flatMap(context => context.pages());
        if (pages.length > 0) {
            console.log('[Playwright] Frame dump for diagnostics:');
            console.log(dumpFrames(pages[0]));
        }
        throw error;
    } finally {
        await browser.close();
    }
}
