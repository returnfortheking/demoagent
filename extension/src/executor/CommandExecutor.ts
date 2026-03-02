import { ChatResponse } from '../client/ApiClient';

type ExecuteFn = (command: string) => Promise<void>;
type ConfirmFn = (message: string) => Promise<boolean>;

export class CommandExecutor {
    constructor(
        private readonly executeFn: ExecuteFn,
        private readonly confirmFn: ConfirmFn
    ) {}

    async handle(response: ChatResponse): Promise<void> {
        if (response.type !== 'action') {
            return;
        }

        const command = response.command ?? '';

        if (!response.requires_confirmation) {
            await this.executeFn(command);
        } else {
            const description = response.description ?? command;
            const message = `确认执行: ${description} (${command})?`;
            const confirmed = await this.confirmFn(message);
            if (confirmed) {
                await this.executeFn(command);
            }
        }
    }
}
