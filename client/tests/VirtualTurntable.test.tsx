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

// Stub SpotifyAPI.connect
vi.mock('../src/Spotify/SpotifyAPI', () => ({
    default: {
        connect: vi.fn(),
        getInstance: vi.fn(), // We'll override per test
        getAlbum: vi.fn(() => Promise.resolve({ id: 'album1', name: 'Album One' })),
        playAlbum: vi.fn(),
    },
}));

// Create a fake player with necessary methods.
const fakePlayer = {
    setVolume: vi.fn(),
    play: vi.fn(),
    pause: vi.fn(),
    previousTrack: vi.fn(),
    nextTrack: vi.fn()
};
// Default stub for getInstance returns fakePlayer.
vi.spyOn(SpotifyPlayer, 'getInstance').mockReturnValue(fakePlayer);

// Spy on WebSocketManagerInstance.send so we can check its calls.
vi.spyOn(WebSocketManagerInstance, 'send').mockImplementation(() => { });

// Stub URL.createObjectURL to return a dummy blob URL.
const dummyBlobURL = 'blob:dummy';
if (!URL.createObjectURL) {
    Object.defineProperty(URL, 'createObjectURL', {
        value: vi.fn().mockReturnValue(dummyBlobURL),
        writable: true,
    });
} else {
    vi.spyOn(URL, 'createObjectURL').mockReturnValue(dummyBlobURL);
}

// Stub fetch for centreLabel and capture endpoints.
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
    needToFetchCapture: null,
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
    needToFetchCapture: null,
    setNeedToFetchCapture: vi.fn(),
};

beforeEach(() => {
    vi.clearAllMocks();
});

describe('VirtualTurntable', () => {
    test('renders error view for non-premium user', () => {
        render(<VirtualTurntable {...defaultPropsNonPremium} />);
        expect(screen.getByText(/Spotify Premium required/i)).toBeInTheDocument();
    });

    test('renders playback view for premium user', async () => {
        render(<VirtualTurntable {...defaultPropsPremium} />);
        await waitFor(() => {
            expect(document.body.className).toBe('projected');
            expect(screen.getByText(/Powered by/i)).toBeInTheDocument();
        });
    });

    test('handles ctrl+wheel event to adjust plate zoom', async () => {
        render(<VirtualTurntable {...defaultPropsPremium} />);
        act(() => {
            window.dispatchEvent(new MouseEvent('mousemove', { bubbles: true }));
        });
        const sliders = await screen.findAllByRole('slider');
        const zoomSlider = sliders.find(input => input.getAttribute('min') === '10');
        expect(zoomSlider).toBeDefined();
        if (zoomSlider) {
            act(() => {
                window.dispatchEvent(new WheelEvent('wheel', { deltaY: 10, ctrlKey: true, bubbles: true }));
            });
            await waitFor(() => {
                expect(zoomSlider).toHaveValue('45');
            });
        }
    });

    test('handles shift+wheel event to adjust volume', async () => {
        const setHostSettingsSpy = vi.fn((updater: any) => updater(dummySettings));
        const props = { ...defaultPropsPremium, setHostSettings: setHostSettingsSpy };
        render(<VirtualTurntable {...props} />);
        act(() => {
            window.dispatchEvent(new WheelEvent('wheel', { deltaY: 10, shiftKey: true, bubbles: true }));
        });
        expect(setHostSettingsSpy).toHaveBeenCalled();
        const updater = setHostSettingsSpy.mock.calls[0][0];
        const newSettings = updater(dummySettings);
        expect(newSettings.volume).toBe(45);
    });

    test('fetches centre label and displays image', async () => {
        render(<VirtualTurntable {...defaultPropsPremium} />);
        await waitFor(() => {
            const labelImg = document.querySelector(`img[src="${dummyBlobURL}"]`);
            expect(labelImg).toBeInTheDocument();
        });
    });

    test('fetches capture image when needToFetchCapture is true', async () => {
        // Override getInstance to force isActive to true.
        vi.spyOn(SpotifyPlayer, 'getInstance').mockImplementation((authToken, setDeviceID, handlePlayerStateChange) => {
            setDeviceID('dummyDevice');
            // Simulate a state with a current track.
            handlePlayerStateChange({ paused: false, track_window: { current_track: dummyTrack } } as any);
            return fakePlayer;
        });
        const setNeedToFetchCaptureSpy = vi.fn();
        const props = { ...defaultPropsPremium, needToFetchCapture: true, setNeedToFetchCapture: setNeedToFetchCaptureSpy };
        render(<VirtualTurntable {...props} />);
        await waitFor(() => {
            const captureImg = document.querySelector('img.albumImage');
            // captureImg should be an HTMLImageElement.
            expect(captureImg).toBeInTheDocument();
            expect(captureImg?.getAttribute('src')).toBe(dummyBlobURL);
        });
        expect(setNeedToFetchCaptureSpy).toHaveBeenCalledWith(null);
    });

    test('updates player volume when hostSettings volume changes', async () => {
        render(<VirtualTurntable {...defaultPropsPremium} />);
        await waitFor(() => {
            expect(fakePlayer.setVolume).toHaveBeenCalledWith(dummySettings.volume);
        });
    });

    test('calls SpotifyAPI.connect on vinyl click when deviceID is defined', async () => {
        vi.spyOn(SpotifyPlayer, 'getInstance').mockImplementation((authToken, setDeviceID, handlePlayerStateChange) => {
            setDeviceID('dummyDevice');
            handlePlayerStateChange({ paused: false, track_window: { current_track: dummyTrack } } as any);
            return fakePlayer;
        });
        const connectSpy = vi.spyOn(SpotifyAPI, 'connect').mockImplementation(() => Promise.resolve());
        render(<VirtualTurntable {...defaultPropsPremium} />);
        const vinyl = document.querySelector('div.vinyl');
        expect(vinyl).toBeDefined();
        if (vinyl) {
            fireEvent.click(vinyl);
        }
        await waitFor(() => {
            expect(connectSpy).toHaveBeenCalledWith('token123', 'dummyDevice');
        });
    });

    test('toggles settings display when settings button is clicked', async () => {
        render(<VirtualTurntable {...defaultPropsPremium} />);
        act(() => {
            window.dispatchEvent(new MouseEvent('mousemove', { bubbles: true }));
        });
        await waitFor(() => {
            expect(screen.getByAltText('Settings')).toBeInTheDocument();
        });
        const settingsButton = screen.getByAltText('Settings');
        fireEvent.click(settingsButton);
        await waitFor(() => {
            const spinButtons = screen.getAllByRole('spinbutton');
            expect(spinButtons.length).toBeGreaterThan(0);
        });
    });

    test('updates client settings when input changes', async () => {
        render(<VirtualTurntable {...defaultPropsPremium} />);
        act(() => {
            window.dispatchEvent(new MouseEvent('mousemove', { bubbles: true }));
        });
        fireEvent.click(screen.getByAltText('Settings'));
        const spinButtons = screen.getAllByRole('spinbutton');
        expect(spinButtons.length).toBeGreaterThan(0);
        const baseplateWidthInput = spinButtons[0];
        fireEvent.change(baseplateWidthInput, { target: { value: '30' } });
        await waitFor(() => {
            expect(baseplateWidthInput).toHaveValue(30);
        });
    });
});
