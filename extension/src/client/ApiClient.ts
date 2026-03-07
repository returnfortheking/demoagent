export interface ChatResponse {
    type: 'action' | 'answer';
    // action fields
    command?: string;
    args?: Record<string, unknown>;
    requires_confirmation?: boolean;
    description?: string;
    // answer fields
    answer?: string;
    sources?: string[];
}

export class ApiClient {
    constructor(private readonly baseUrl: string) {}

    buildUrl(path: string): string {
        const cleanedBaseUrl = this.baseUrl.replace(/\/$/, '');
        const normalizedPath = path.startsWith('/') ? path : `/${path}`;
        return cleanedBaseUrl + normalizedPath;
    }

    parseResponse(raw: unknown): ChatResponse {
        if (typeof raw !== 'object' || raw === null) {
            throw new Error('Invalid response: expected object');
        }
        const r = raw as Record<string, unknown>;
        if (r['type'] !== 'action' && r['type'] !== 'answer') {
            throw new Error(`Invalid response type: ${String(r['type'])}`);
        }
        return {
            type: r['type'] as 'action' | 'answer',
            command: typeof r['command'] === 'string' ? r['command'] : undefined,
            args: (typeof r['args'] === 'object' && r['args'] !== null)
                ? r['args'] as Record<string, unknown> : undefined,
            requires_confirmation: typeof r['requires_confirmation'] === 'boolean'
                ? r['requires_confirmation'] : undefined,
            description: typeof r['description'] === 'string' ? r['description'] : undefined,
            answer: typeof r['answer'] === 'string' ? r['answer'] : undefined,
            sources: Array.isArray(r['sources']) ? r['sources'] as string[] : undefined,
        };
    }

    async sendMessage(message: string, threadId: string): Promise<ChatResponse> {
        const url = this.buildUrl('/chat');
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message, thread_id: threadId })
        });
        const data: unknown = await response.json();
        return this.parseResponse(data);
    }
}

export const defaultClient = new ApiClient('http://localhost:8000');
