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

    parseResponse(raw: object): ChatResponse {
        return raw as ChatResponse;
    }

    async sendMessage(message: string, threadId: string): Promise<ChatResponse> {
        const url = this.buildUrl('/chat');
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message, thread_id: threadId })
        });
        const data = await response.json() as object;
        return this.parseResponse(data);
    }
}

export const defaultClient = new ApiClient('http://localhost:8000');
