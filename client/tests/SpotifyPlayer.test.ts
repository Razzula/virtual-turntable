import { vi, describe, test, expect, beforeEach } from "vitest";
import { SpotifyPlayer } from "../src/Spotify/SpotifyPlayer";

// --- Global Mocks for Spotify SDK ---
const mockPlayerMethods = {
    connect: vi.fn(),
    togglePlay: vi.fn(),
    resume: vi.fn(),
    pause: vi.fn(),
    nextTrack: vi.fn(),
    previousTrack: vi.fn(),
    setVolume: vi.fn(),
    addListener: vi.fn(),
};
const SpotifyPlayerMock = vi.fn(() => mockPlayerMethods);
globalThis.Spotify = {
    Player: SpotifyPlayerMock,
} as any;

// Let document.createElement return a real Node for scripts.
const originalCreateElement = document.createElement.bind(document);
vi.spyOn(document, "createElement").mockImplementation((tagName: string) => {
    if (tagName === "script") {
        const script = originalCreateElement(tagName);
        script.async = true;
        script.src = "";
        return script;
    }
    return originalCreateElement(tagName);
});

// Dummy callbacks
const mockSetDeviceID = vi.fn();
const mockHandleStateChange = vi.fn();

beforeEach(() => {
    vi.clearAllMocks();
});

describe("SpotifyPlayer", () => {
    test("should initialize and load the SDK script", () => {
        new SpotifyPlayer("test-token", mockSetDeviceID, mockHandleStateChange);
        expect(document.createElement).toHaveBeenCalledWith("script");
    });

    test("should log error when SDK fails to load", async () => {
        const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => { });
        // Override document.body.appendChild to simulate script error.
        const originalAppendChild = document.body.appendChild;
        document.body.appendChild = (node: Node) => {
            if (node instanceof HTMLScriptElement && node.onerror) {
                node.onerror(new Error("Script failed"));
            }
            return originalAppendChild.call(document.body, node);
        };

        new SpotifyPlayer("test-token", mockSetDeviceID, mockHandleStateChange);
        // Allow microtask queue to flush.
        await new Promise((r) => setTimeout(r, 0));
        expect(consoleErrorSpy).toHaveBeenCalledWith(
            "Error during SDK loading:",
            expect.any(Error)
        );
        document.body.appendChild = originalAppendChild;
    });

    test("should create Spotify Player instance when SDK is ready", () => {
        new SpotifyPlayer("test-token", mockSetDeviceID, mockHandleStateChange);
        window.onSpotifyWebPlaybackSDKReady();
        expect(SpotifyPlayerMock).toHaveBeenCalledWith({
            name: "Virtual Turntable",
            getOAuthToken: expect.any(Function),
            volume: 0.5,
        });
    });

    test("should call setDeviceID on ready event", () => {
        new SpotifyPlayer("test-token", mockSetDeviceID, mockHandleStateChange);
        window.onSpotifyWebPlaybackSDKReady();
        // Simulate 'ready' event.
        const readyCall = mockPlayerMethods.addListener.mock.calls.find(
            (call) => call[0] === "ready"
        );
        expect(readyCall).toBeDefined();
        if (readyCall) {
            readyCall[1]({ device_id: "dummyDevice" });
            expect(mockSetDeviceID).toHaveBeenCalledWith("dummyDevice");
        }
    });

    test("should log not_ready event", () => {
        const consoleLogSpy = vi.spyOn(console, "log").mockImplementation(() => { });
        new SpotifyPlayer("test-token", mockSetDeviceID, mockHandleStateChange);
        window.onSpotifyWebPlaybackSDKReady();
        const notReadyCall = mockPlayerMethods.addListener.mock.calls.find(
            (call) => call[0] === "not_ready"
        );
        expect(notReadyCall).toBeDefined();
        if (notReadyCall) {
            notReadyCall[1]({ device_id: "dummyDevice" });
            expect(consoleLogSpy).toHaveBeenCalledWith("Device ID has gone offline", "dummyDevice");
        }
    });

    test("should call handlePlayerStateChange on player_state_changed event", () => {
        new SpotifyPlayer("test-token", mockSetDeviceID, mockHandleStateChange);
        window.onSpotifyWebPlaybackSDKReady();
        const stateChangedCall = mockPlayerMethods.addListener.mock.calls.find(
            (call) => call[0] === "player_state_changed"
        );
        expect(stateChangedCall).toBeDefined();
        if (stateChangedCall) {
            const dummyState = { paused: false, track_window: { current_track: { id: "track1" } } };
            stateChangedCall[1](dummyState);
            expect(mockHandleStateChange).toHaveBeenCalledWith(dummyState);
        }
    });

    test("should log error for autoplay_failed event", () => {
        const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => { });
        new SpotifyPlayer("test-token", mockSetDeviceID, mockHandleStateChange);
        window.onSpotifyWebPlaybackSDKReady();
        const autoplayCall = mockPlayerMethods.addListener.mock.calls.find(
            (call) => call[0] === "autoplay_failed"
        );
        expect(autoplayCall).toBeDefined();
        if (autoplayCall) {
            autoplayCall[1]();
            expect(consoleErrorSpy).toHaveBeenCalledWith(
                "Autoplay failed. This may be due to DRM issues or autoplay restrictions."
            );
        }
    });

    test("should log error for initialization_error event", () => {
        const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => { });
        new SpotifyPlayer("test-token", mockSetDeviceID, mockHandleStateChange);
        window.onSpotifyWebPlaybackSDKReady();
        const initErrorCall = mockPlayerMethods.addListener.mock.calls.find(
            (call) => call[0] === "initialization_error"
        );
        expect(initErrorCall).toBeDefined();
        if (initErrorCall) {
            initErrorCall[1]({ message: "init error" });
            expect(consoleErrorSpy).toHaveBeenCalledWith("Initialisation error:", "init error");
        }
    });

    test("should log error for authentication_error event", () => {
        const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => { });
        new SpotifyPlayer("test-token", mockSetDeviceID, mockHandleStateChange);
        window.onSpotifyWebPlaybackSDKReady();
        const authErrorCall = mockPlayerMethods.addListener.mock.calls.find(
            (call) => call[0] === "authentication_error"
        );
        expect(authErrorCall).toBeDefined();
        if (authErrorCall) {
            authErrorCall[1]({ message: "auth error" });
            expect(consoleErrorSpy).toHaveBeenCalledWith("Authentication error:", "auth error");
        }
    });

    test("should log error for account_error event", () => {
        const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => { });
        new SpotifyPlayer("test-token", mockSetDeviceID, mockHandleStateChange);
        window.onSpotifyWebPlaybackSDKReady();
        const accountErrorCall = mockPlayerMethods.addListener.mock.calls.find(
            (call) => call[0] === "account_error"
        );
        expect(accountErrorCall).toBeDefined();
        if (accountErrorCall) {
            accountErrorCall[1]({ message: "account error" });
            expect(consoleErrorSpy).toHaveBeenCalledWith("Account error:", "account error");
        }
    });

    test("should call connect() on player when initialized", () => {
        new SpotifyPlayer("test-token", mockSetDeviceID, mockHandleStateChange);
        window.onSpotifyWebPlaybackSDKReady();
        expect(mockPlayerMethods.connect).toHaveBeenCalled();
    });

    test("should call play() when play() is triggered", () => {
        const instance = new SpotifyPlayer("test-token", mockSetDeviceID, mockHandleStateChange);
        window.onSpotifyWebPlaybackSDKReady();
        instance.play();
        expect(mockPlayerMethods.resume).toHaveBeenCalled();
    });

    test("should call pause() when pause() is triggered", () => {
        const instance = new SpotifyPlayer("test-token", mockSetDeviceID, mockHandleStateChange);
        window.onSpotifyWebPlaybackSDKReady();
        instance.pause();
        expect(mockPlayerMethods.pause).toHaveBeenCalled();
    });

    test("should call nextTrack() when nextTrack() is triggered", () => {
        const instance = new SpotifyPlayer("test-token", mockSetDeviceID, mockHandleStateChange);
        window.onSpotifyWebPlaybackSDKReady();
        instance.nextTrack();
        expect(mockPlayerMethods.nextTrack).toHaveBeenCalled();
    });

    test("should call previousTrack() when previousTrack() is triggered", () => {
        const instance = new SpotifyPlayer("test-token", mockSetDeviceID, mockHandleStateChange);
        window.onSpotifyWebPlaybackSDKReady();
        instance.previousTrack();
        expect(mockPlayerMethods.previousTrack).toHaveBeenCalled();
    });

    test("should set volume when setVolume() is triggered", () => {
        const instance = new SpotifyPlayer("test-token", mockSetDeviceID, mockHandleStateChange);
        window.onSpotifyWebPlaybackSDKReady();
        instance.setVolume(50);
        expect(mockPlayerMethods.setVolume).toHaveBeenCalledWith(0.5);
    });
});
