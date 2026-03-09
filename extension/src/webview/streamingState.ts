export interface StreamMessage {
    text: string;
    finalized?: boolean;
}

export interface StreamingState {
    statusText: string;
    messages: StreamMessage[];
    _pendingText: string;
}

export function initialState(): StreamingState {
    return { statusText: '', messages: [], _pendingText: '' };
}

export function applyStreamEvent(
    state: StreamingState,
    event: { type: string; [key: string]: unknown }
): StreamingState {
    switch (event['type']) {
        case 'statusUpdate':
            return { ...state, statusText: event['text'] as string };
        case 'streamChunk':
            return {
                ...state,
                statusText: '',
                _pendingText: state._pendingText + (event['delta'] as string),
            };
        case 'streamDone': {
            const messages: StreamMessage[] = [
                ...state.messages,
                { text: state._pendingText, finalized: true },
            ];
            return { statusText: '', messages, _pendingText: '' };
        }
        case 'actionDone': {
            const messages: StreamMessage[] = [
                ...state.messages,
                { text: `已执行：${event['description'] as string}` },
            ];
            return { statusText: '', messages, _pendingText: '' };
        }
        default:
            return state;
    }
}
