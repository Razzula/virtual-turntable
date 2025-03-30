import { vi, describe, test, expect, beforeEach } from "vitest";
import SpotifyAPI from "../src/APIs/Spotify/SpotifyAPI";
import { Album, User } from "../src/types/Spotify";

// Mock global fetch
global.fetch = vi.fn();

describe("SpotifyAPI", () => {
    const mockAuthToken = "test-token";

    beforeEach(() => {
        vi.resetAllMocks(); // Reset mocks before each test
    });

    test("connect() should call Spotify API with correct parameters", async () => {
        global.fetch = vi.fn().mockResolvedValue({ ok: true });

        await SpotifyAPI.connect(mockAuthToken, "device123");

        expect(global.fetch).toHaveBeenCalledWith(
            "https://api.spotify.com/v1/me/player",
            expect.objectContaining({
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${mockAuthToken}`,
                },
                body: JSON.stringify({ device_ids: ["device123"] }),
            })
        );
    });

    test("getAlbum() should return album data", async () => {
        const mockAlbum: Album = { id: "album123", name: "Test Album" } as Album;
        global.fetch = vi.fn().mockResolvedValue({
            json: vi.fn().mockResolvedValue(mockAlbum),
        });

        const album = await SpotifyAPI.getAlbum(mockAuthToken, "album123");

        expect(global.fetch).toHaveBeenCalledWith(
            "https://api.spotify.com/v1/albums/album123",
            expect.objectContaining({
                method: "GET",
                headers: expect.objectContaining({
                    "Authorization": `Bearer ${mockAuthToken}`,
                }),
            })
        );
        expect(album).toEqual(mockAlbum);
    });

    test("playAlbum() should send correct request", async () => {
        global.fetch = vi.fn().mockResolvedValue({ ok: true });

        await SpotifyAPI.playAlbum(mockAuthToken, "album123", 2, 5000);

        expect(global.fetch).toHaveBeenCalledWith(
            "https://api.spotify.com/v1/me/player/play",
            expect.objectContaining({
                method: "PUT",
                body: JSON.stringify({
                    context_uri: "spotify:album:album123",
                    offset: { position: 2 },
                    position_ms: 5000,
                }),
            })
        );
    });

    test("getOwnProfile() should return user profile", async () => {
        const mockUser: User = { id: "user123", display_name: "Test User" } as User;
        global.fetch = vi.fn().mockResolvedValue({
            json: vi.fn().mockResolvedValue(mockUser),
        });

        const user = await SpotifyAPI.getOwnProfile(mockAuthToken);

        expect(user).toEqual(mockUser);
        expect(global.fetch).toHaveBeenCalledWith(
            "https://api.spotify.com/v1/me",
            expect.objectContaining({
                method: "GET",
            })
        );
    });

    test("getUserProfile() should return a specific user profile", async () => {
        const mockUser: User = { id: "user456", display_name: "Another User" } as User;
        global.fetch = vi.fn().mockResolvedValue({
            json: vi.fn().mockResolvedValue(mockUser),
        });

        const user = await SpotifyAPI.getUserProfile(mockAuthToken, "user456");

        expect(user).toEqual(mockUser);
        expect(global.fetch).toHaveBeenCalledWith(
            "https://api.spotify.com/v1/users/user456",
            expect.objectContaining({
                method: "GET",
            })
        );
    });

    test("getPlaylistAlbums() should fetch albums from a playlist", async () => {
        global.fetch = vi.fn()
            .mockResolvedValueOnce({
                json: vi.fn().mockResolvedValue({
                    items: [{ track: { album: { id: "album1" } } }],
                    next: null
                })
            })
            .mockResolvedValueOnce({
                json: vi.fn().mockResolvedValue({
                    albums: [{ id: "album1", name: "Test Album" }]
                })
            });

        const albums = await SpotifyAPI.getPlaylistAlbums(mockAuthToken, "playlist123");

        expect(albums).toEqual([{ id: "album1", name: "Test Album" }]);
        expect(global.fetch).toHaveBeenCalledTimes(2);
    });
});
