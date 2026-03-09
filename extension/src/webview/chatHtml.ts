export function getHtmlContent(): string {
    return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="Content-Security-Policy"
        content="default-src 'none'; script-src 'unsafe-inline';">
  <title>HiSpark AI Chat</title>
</head>
<body>
  <div id="status-bar"></div>
  <div id="messages"></div>
  <div id="input-area">
    <input id="chat-input" type="text" placeholder="输入消息..." />
    <button id="send-btn">发送</button>
    <button id="stream-btn">流式发送</button>
  </div>
  <script>
    const vscode = acquireVsCodeApi();
    document.getElementById('send-btn').addEventListener('click', () => {
      const input = document.getElementById('chat-input');
      const message = input.value.trim();
      if (!message) return;
      vscode.postMessage({ type: 'chat', message });
      input.value = '';
    });
    document.getElementById('stream-btn').addEventListener('click', () => {
      const input = document.getElementById('chat-input');
      const message = input.value.trim();
      if (!message) return;
      vscode.postMessage({ type: 'stream', message });
      input.value = '';
    });
    window.addEventListener('message', event => {
      const data = event.data;
      const statusBar = document.getElementById('status-bar');
      const messages = document.getElementById('messages');
      if (data.type === 'statusUpdate') {
        statusBar.textContent = data.text;
      } else if (data.type === 'streamChunk') {
        statusBar.textContent = '';
        let bubble = document.getElementById('stream-bubble');
        if (!bubble) {
          bubble = document.createElement('div');
          bubble.id = 'stream-bubble';
          messages.appendChild(bubble);
        }
        bubble.textContent += data.delta;
      } else if (data.type === 'streamDone') {
        const bubble = document.getElementById('stream-bubble');
        if (bubble) { bubble.removeAttribute('id'); }
      } else if (data.type === 'actionDone') {
        statusBar.textContent = '';
        const el = document.createElement('div');
        el.textContent = '已执行：' + data.description;
        messages.appendChild(el);
      } else {
        const el = document.createElement('div');
        el.textContent = JSON.stringify(data);
        messages.appendChild(el);
      }
    });
  </script>
</body>
</html>`;
}
