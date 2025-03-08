import { vi, describe, test, expect, beforeEach } from "vitest";
import { SpotifyPlayer } from "../src/Spotify/SpotifyPlayer";

// Setup a global mock for the Spotify SDK
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

// Instead of returning a fake object, let document.createElement return a real Node.
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

// Dummy functions for setDeviceID and state change handling
const mockSetDeviceID = vi.fn();
const mockHandleStateChange = vi.fn();

describe("SpotifyPlayer", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    test("should initialize and load the SDK script", () => {
        const mockAuthToken = "test-token";
        new SpotifyPlayer(mockAuthToken, mockSetDeviceID, mockHandleStateChange);

        // Check that a script element is created
        expect(document.createElement).toHaveBeenCalledWith("script");
    });

    test("should create Spotify Player instance when SDK is ready", () => {
        const mockAuthToken = "test-token";
        new SpotifyPlayer(mockAuthToken, mockSetDeviceID, mockHandleStateChange);

        // Simulate SDK loaded callback
        window.onSpotifyWebPlaybackSDKReady();

        expect(SpotifyPlayerMock).toHaveBeenCalledWith({
            name: "Virtual Turntable",
            getOAuthToken: expect.any(Function),
            volume: 0.5,
        });
    });

    test("should call connect() on player when initialized", () => {
        const mockAuthToken = "test-token";
        new SpotifyPlayer(mockAuthToken, mockSetDeviceID, mockHandleStateChange);
        window.onSpotifyWebPlaybackSDKReady();

        expect(mockPlayerMethods.connect).toHaveBeenCalled();
    });

    test("should call play() when play() is triggered", () => {
        const mockAuthToken = "test-token";
        const playerInstance = new SpotifyPlayer(mockAuthToken, mockSetDeviceID, mockHandleStateChange);
        window.onSpotifyWebPlaybackSDKReady();

        playerInstance.play();
        expect(mockPlayerMethods.resume).toHaveBeenCalled();
    });

    test("should call pause() when pause() is triggered", () => {
        const mockAuthToken = "test-token";
        const playerInstance = new SpotifyPlayer(mockAuthToken, mockSetDeviceID, mockHandleStateChange);
        window.onSpotifyWebPlaybackSDKReady();

        playerInstance.pause();
        expect(mockPlayerMethods.pause).toHaveBeenCalled();
    });

    test("should call nextTrack() when nextTrack() is triggered", () => {
        const mockAuthToken = "test-token";
        const playerInstance = new SpotifyPlayer(mockAuthToken, mockSetDeviceID, mockHandleStateChange);
        window.onSpotifyWebPlaybackSDKReady();

        playerInstance.nextTrack();
        expect(mockPlayerMethods.nextTrack).toHaveBeenCalled();
    });

    test("should call previousTrack() when previousTrack() is triggered", () => {
        const mockAuthToken = "test-token";
        const playerInstance = new SpotifyPlayer(mockAuthToken, mockSetDeviceID, mockHandleStateChange);
        window.onSpotifyWebPlaybackSDKReady();

        playerInstance.previousTrack();
        expect(mockPlayerMethods.previousTrack).toHaveBeenCalled();
    });

    test("should set volume when setVolume() is triggered", () => {
        const mockAuthToken = "test-token";
        const playerInstance = new SpotifyPlayer(mockAuthToken, mockSetDeviceID, mockHandleStateChange);
        window.onSpotifyWebPlaybackSDKReady();

        playerInstance.setVolume(50);
        expect(mockPlayerMethods.setVolume).toHaveBeenCalledWith(0.5);
    });
});
