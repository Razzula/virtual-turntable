// tests/RemoteController.test.tsx
import '@testing-library/jest-dom';
import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { vi, describe, test, expect, beforeEach } from "vitest";
import RemoteController from "../src/RemoteController";
import SpotifyAPI from "../src/Spotify/SpotifyAPI";
import WebSocketManagerInstance from "../src/WebSocketManager";

// Use the correct module path for mocking SpotifyAPI
vi.mock("../src/Spotify/SpotifyAPI", () => ({
    default: {
        getUserProfile: vi.fn(),
        getPlaylistAlbums: vi.fn(),
    },
}));

// Mock fetch for the playlist call
const mockPlaylistResponse = { playlistID: "playlist123" };
global.fetch = vi.fn().mockImplementation((url) => {
    if (url === "/virtual-turntable/server/playlist") {
        return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockPlaylistResponse),
        });
    }
    return Promise.resolve({ ok: false });
});

// Spy on WebSocket send
vi.spyOn(WebSocketManagerInstance, "send").mockImplementation(() => { });

describe("RemoteController", () => {
    const dummyUserProfile = {
        id: "user1",
        display_name: "User One",
        external_urls: { spotify: "https://open.spotify.com/user/user1" },
        images: [{ url: "user1.jpg" }],
    };

    const dummyHostUserProfile = {
        id: "host1",
        display_name: "Host One",
        external_urls: { spotify: "https://open.spotify.com/user/host1" },
        images: [{ url: "host1.jpg" }],
    };

    const dummyAlbum = {
        id: "album1",
        name: "Album One",
        images: [{ url: "album1.jpg" }],
        external_urls: { spotify: "https://open.spotify.com/album/album1" },
    };

    const dummyTrack = {
        id: "track1",
        name: "Track One",
    };

    const defaultProps = {
        authToken: "token123",
        userProfile: dummyUserProfile,
        isPlaying: false,
        currentAlbum: dummyAlbum,
        currentTrack: dummyTrack,
        handleUpload: vi.fn(),
        hostUserID: "host1",
        hostSettings: {
            volume: 50,
            enableRemote: true,
            enforceSignature: false,
        },
        isHostSettingsUpdateLocal: { current: false } as React.MutableRefObject<boolean>,
    };

    beforeEach(() => {
        (SpotifyAPI.getUserProfile as vi.Mock).mockResolvedValue(dummyHostUserProfile);
        (SpotifyAPI.getPlaylistAlbums as vi.Mock).mockResolvedValue([dummyAlbum]);
        vi.clearAllMocks();
    });

    test("renders controller when authToken is provided", async () => {
        render(<RemoteController {...defaultProps} />);
        // Wait for getUserProfile to be called
        await waitFor(() => {
            expect(SpotifyAPI.getUserProfile).toHaveBeenCalledWith("token123", "host1");
        });
        // Check that a heading with "Virtual Turntable" is in the document
        expect(screen.getByRole("heading", { name: /Virtual Turntable/i })).toBeInTheDocument();
    });

    test("renders login view when authToken is empty", () => {
        render(<RemoteController {...defaultProps} authToken="" />);
        expect(screen.getByRole("heading", { name: /Login with Spotify/i })).toBeInTheDocument();
    });

    test("updates volume and sends WebSocket message", async () => {
        const props = { ...defaultProps, isHostSettingsUpdateLocal: { current: false } };
        render(<RemoteController {...props} />);
        // Wait for the volume slider to appear
        const slider = await screen.findByRole("slider");
        // Simulate volume change to 70
        fireEvent.change(slider, { target: { value: "70" } });
        await waitFor(() => {
            // Use toHaveAttribute since slider.value is a string attribute
            expect(slider).toHaveAttribute("value", "70");
            expect(WebSocketManagerInstance.send).toHaveBeenCalledWith(
                JSON.stringify({ command: "settings", value: { ...props.hostSettings, volume: 70 } })
            );
        });
    });

    test("handles album click and sends playAlbum command", async () => {
        const props = { ...defaultProps, userProfile: dummyHostUserProfile };
        const { container } = render(<RemoteController {...props} />);
        // Wait until the album name appears in the sidebar
        await waitFor(() => expect(screen.getByText("Album One")).toBeInTheDocument());
        // Then query the rendered DOM for the sidebar image
        const sidebarAlbum = container.querySelector("img.albumArtMini");
        expect(sidebarAlbum).toBeDefined();
        if (sidebarAlbum) {
            fireEvent.click(sidebarAlbum);
            expect(WebSocketManagerInstance.send).toHaveBeenCalledWith(
                JSON.stringify({ command: "playAlbum", value: dummyAlbum.id })
            );
        }
    });

});
