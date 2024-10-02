class WebSocketManager {
    private static instance: WebSocketManager;
    private webSocket: WebSocket | null;

    private constructor() {
        this.webSocket = null;
    }

    public static get Instance(): WebSocketManager {
        if (!this.instance) {
            this.instance = new WebSocketManager();
        }
        return this.instance;
    }

    public connect(url: string, onMessage: (e: MessageEvent) => void): void {
        if (this.webSocket !== null) {
            console.error('WebSocket connection already established');
            return;
        }
        this.webSocket = new WebSocket(url);

        this.webSocket.onopen= () => {
            console.log(`Connected to WebSocket server (${url})`);
        };

        this.webSocket.onclose = () => {
            this.webSocket = null;
        };

        this.webSocket.onmessage = onMessage;
    }

    public disconnect(): void {
        if (this.webSocket !== null) {
            this.webSocket.close();
            this.webSocket = null;
        }
    }

    public forceConnect(url: string, onMessage: () => void): void {
        if (this.webSocket !== null) {
            this.webSocket.close();
        }
        this.connect(url, onMessage);
    }

    public send(message: string): void {
        if (this.webSocket !== null) {
            this.webSocket.send(message);
        }
    }
}

const WebSocketManagerInstance = WebSocketManager.Instance;

export default WebSocketManagerInstance;
