// tests/VirtualTurntable.test.tsx
import '@testing-library/jest-dom';
import React from 'react';
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';
import { vi, describe, test, expect, beforeEach } from 'vitest';
import VirtualTurntable from '../src/VirtualTurntable';
import SpotifyPlayer from '../src/Spotify/SpotifyPlayer';
import WebSocketManagerInstance from '../src/WebSocketManager';
import SpotifyAPI from '../src/Spotify/SpotifyAPI';

// --- Mocks & Stubs ---

// Stub SpotifyAPI.connect (others if needed)
vi.mock('../src/Spotify/SpotifyAPI', () => ({
    default: {
        connect: vi.fn(),
    },
}));

// Stub SpotifyPlayer.getInstance to return a fake player with setVolume method
const fakePlayer = { setVolume: vi.fn() };
vi.spyOn(SpotifyPlayer, 'getInstance').mockReturnValue(fakePlayer);

// Spy on WebSocketManagerInstance.send so we can check its calls
vi.spyOn(WebSocketManagerInstance, 'send').mockImplementation(() => { });

// Stub URL.createObjectURL to return a dummy blob URL
const dummyBlobURL = 'blob:dummy';
if (!URL.createObjectURL) {
    Object.defineProperty(URL, 'createObjectURL', {
        value: vi.fn().mockReturnValue(dummyBlobURL),
        writable: true,
    });
} else {
    vi.spyOn(URL, 'createObjectURL').mockReturnValue(dummyBlobURL);
}


// Stub fetch for centreLabel and capture endpoints
const centreLabelResponse = {
    imageData: btoa('dummydata'),
    metadata: { colour: 'black', marble: true },
};
global.fetch = vi.fn((url, options) => {
    if (url === '/virtual-turntable/server/centreLabel') {
        return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(centreLabelResponse),
        });
    }
    if (url === '/virtual-turntable/server/capture') {
        return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ imageData: btoa('captureddata') }),
        });
    }
    return Promise.resolve({ ok: false });
});

// --- Dummy Props ---
const dummyUserProfileNonPremium = {
    id: 'user1',
    product: 'free', // non-premium
    display_name: 'User One',
    external_urls: { spotify: 'https://open.spotify.com/user/user1' },
    images: [{ url: 'user1.jpg' }],
};

const dummyUserProfilePremium = {
    id: 'user1',
    product: 'premium',
    display_name: 'User One',
    external_urls: { spotify: 'https://open.spotify.com/user/user1' },
    images: [{ url: 'user1.jpg' }],
};

const dummyAlbum = {
    id: 'album1',
    name: 'Album One',
    release_date: '2020-01-01',
    artists: [{ name: 'Artist One' }],
    images: [{ url: 'album1.jpg' }],
    external_urls: { spotify: 'https://open.spotify.com/album/album1' },
};

const dummyTrack = {
    id: 'track1',
    name: 'Track One',
};

const dummySettings = {
    volume: 50,
    enableRemote: true,
    enforceSignature: false,
    enableMotor: false,
};

const defaultPropsPremium = {
    authToken: 'token123',
    userProfile: dummyUserProfilePremium,
    isPlaying: false,
    setIsPlaying: vi.fn(),
    currentAlbum: dummyAlbum,
    setCurrentAlbum: vi.fn(),
    currentTrack: dummyTrack,
    setCurrentTrack: vi.fn(),
    hostSettings: dummySettings,
    setHostSettings: vi.fn(),
    isHostSettingsUpdateLocal: { current: false },
    hostUserID: 'user1',
    needToFetchCapture: false,
    setNeedToFetchCapture: vi.fn(),
};

const defaultPropsNonPremium = {
    authToken: 'token123',
    userProfile: dummyUserProfileNonPremium,
    isPlaying: false,
    setIsPlaying: vi.fn(),
    currentAlbum: null,
    setCurrentAlbum: vi.fn(),
    currentTrack: null,
    setCurrentTrack: vi.fn(),
    hostSettings: dummySettings,
    setHostSettings: vi.fn(),
    isHostSettingsUpdateLocal: { current: false },
    hostUserID: 'user1',
    needToFetchCapture: false,
    setNeedToFetchCapture: vi.fn(),
};

// --- Test Suite ---
describe('VirtualTurntable', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    test('renders error view for non-premium user', () => {
        render(<VirtualTurntable {...defaultPropsNonPremium} />);
        expect(screen.getByText(/Spotify Premium required/i)).toBeInTheDocument();
    });

    test('renders playback view for premium user', async () => {
        render(<VirtualTurntable {...defaultPropsPremium} />);
        // Wait for body class change & key text
        await waitFor(() => {
            expect(document.body.className).toBe('projected');
            expect(screen.getByText(/Powered by/i)).toBeInTheDocument();
        });
    });

    test('handles ctrl+wheel event to adjust plate zoom', async () => {
        render(<VirtualTurntable {...defaultPropsPremium} />);
        // Activate floating controls via mouse movement
        fireEvent.mouseMove(window);
        // Wait for a slider in the floating controls to appear.
        const sliders = await screen.findAllByRole('slider');
        // Assume the first slider (with min="10") is the zoom slider.
        const zoomSlider = sliders.find(input => input.getAttribute('min') === '10');
        expect(zoomSlider).toBeDefined();
        if (zoomSlider) {
            // Initial plateZoom is 50. Simulate ctrl+wheel event that should reduce it by 5.
            act(() => {
                window.dispatchEvent(new WheelEvent('wheel', { deltaY: 10, ctrlKey: true, bubbles: true }));
            });
            // Wait for re-render; expect the zoom slider's value to be updated (e.g. "45")
            await waitFor(() => {
                expect(zoomSlider).toHaveValue('45');
            });
        }
    });

    test('fetches centre label and displays image', async () => {
        render(<VirtualTurntable {...defaultPropsPremium} />);
        // currentAlbum is provided so the centre label effect should run.
        // Wait until an image with src equal to dummyBlobURL appears.
        await waitFor(() => {
            const labelImg = document.querySelector(`img[src="${dummyBlobURL}"]`);
            expect(labelImg).toBeInTheDocument();
        });
    });

    test('updates player volume when hostSettings volume changes', async () => {
        render(<VirtualTurntable {...defaultPropsPremium} />);
        // useEffect should call fakePlayer.setVolume with the volume from hostSettings.
        await waitFor(() => {
            expect(fakePlayer.setVolume).toHaveBeenCalledWith(dummySettings.volume);
        });
    });
});
