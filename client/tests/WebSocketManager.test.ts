import { describe, test, expect, vi, beforeEach, afterEach } from "vitest";
import WebSocketManager from "../src/WebSocketManager";

// A global variable to capture the created mock WebSocket instance
let createdWebSocket: MockWebSocket | null = null;

// Define a mock WebSocket class
class MockWebSocket {
    public onopen: (() => void) | null = null;
    public onclose: (() => void) | null = null;
    public onerror: ((error: any) => void) | null = null;
    public onmessage: ((e: MessageEvent) => void) | null = null;
    public sentMessages: string[] = [];
    public url: string;

    constructor(url: string) {
        this.url = url;
        createdWebSocket = this;
    }

    send(message: string) {
        this.sentMessages.push(message);
    }

    close() {
        if (this.onclose) {
            this.onclose();
        }
    }
}

// Replace the global WebSocket with our mock
(global as any).WebSocket = MockWebSocket;

describe("WebSocketManager", () => {
    beforeEach(() => {
        // Reset the singleton's connection state
        (WebSocketManager as any).webSocket = null;
        createdWebSocket = null;
        vi.spyOn(console, "error").mockImplementation(() => { });
        vi.spyOn(console, "log").mockImplementation(() => { });
    });

    afterEach(() => {
        vi.restoreAllMocks();
        WebSocketManager.disconnect();
    });

    test("connect() should create a new WebSocket and store it on onopen", () => {
        const url = "ws://test";
        const onMessage = vi.fn();

        WebSocketManager.connect(url, onMessage);
        // Before onopen fires, the internal webSocket is still null.
        expect((WebSocketManager as any).webSocket).toBeNull();

        // Simulate connection opening.
        createdWebSocket?.onopen?.();

        expect((WebSocketManager as any).webSocket).toBe(createdWebSocket);
        expect(createdWebSocket?.onmessage).toBe(onMessage);
    });

    test("connect() should not reconnect if already connected", () => {
        const url = "ws://test";
        const onMessage = vi.fn();

        WebSocketManager.connect(url, onMessage);
        createdWebSocket?.onopen?.(); // simulate connection

        // Attempt a second connection.
        WebSocketManager.connect("ws://another", onMessage);
        expect(console.error).toHaveBeenCalledWith("WebSocket connection already established");
    });

    test("disconnect() should close the connection and reset webSocket", () => {
        const url = "ws://test";
        const onMessage = vi.fn();

        WebSocketManager.connect(url, onMessage);
        createdWebSocket?.onopen?.(); // simulate connection
        expect((WebSocketManager as any).webSocket).toBe(createdWebSocket);

        WebSocketManager.disconnect();
        expect((WebSocketManager as any).webSocket).toBeNull();
    });

    test("forceConnect() should close existing connection and create a new one", () => {
        const url = "ws://test";
        const onMessage = vi.fn();

        // Create first connection
        WebSocketManager.connect(url, onMessage);
        createdWebSocket?.onopen?.(); // simulate connection
        const firstWebSocket = createdWebSocket;

        // Spy on the close method of the first connection.
        const closeSpy = vi.spyOn(firstWebSocket as MockWebSocket, "close");

        // Force a new connection.
        WebSocketManager.forceConnect("ws://new", onMessage);
        createdWebSocket?.onopen?.(); // simulate new connection
        const newWebSocket = createdWebSocket;

        expect(closeSpy).toHaveBeenCalled();
        expect((WebSocketManager as any).webSocket).toBe(newWebSocket);
        expect(newWebSocket.url).toBe("ws://new");
    });

    test("send() should call send on the underlying WebSocket", () => {
        const url = "ws://test";
        const onMessage = vi.fn();

        WebSocketManager.connect(url, onMessage);
        createdWebSocket?.onopen?.(); // simulate connection

        const message = "hello";
        WebSocketManager.send(message);
        expect(createdWebSocket?.sentMessages).toContain(message);
    });
});
