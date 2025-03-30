import '@testing-library/jest-dom';
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { vi, describe, test, expect, beforeEach } from 'vitest';
import App from '../src/App';

// --- Stub Child Components ---
vi.mock('../src/VirtualTurntable', () => ({
    default: () => <div data-testid="virtual-turntable">VirtualTurntable View</div>,
}));
vi.mock('../src/RemoteController', () => ({
    default: () => <div data-testid="remote-controller">RemoteController View</div>,
}));

// --- Stub SpotifyAPI ---
vi.mock('../src/APIs/Spotify/SpotifyAPI', () => ({
    default: {
        getOwnProfile: vi.fn(() =>
            Promise.resolve({
                id: 'user1',
                product: 'premium',
                display_name: 'User One',
                external_urls: { spotify: 'https://open.spotify.com/user/user1' },
                images: [{ url: 'user1.jpg' }],
            })
        ),
        getAlbum: vi.fn(() => Promise.resolve({ id: 'album1', name: 'Album One' })),
        playAlbum: vi.fn(),
    },
}));

// --- Stub WebSocketManager ---
vi.mock('../src/WebSocketManager', () => ({
    default: {
        connect: vi.fn(),
        send: vi.fn(),
    },
}));

// --- Override global.fetch ---
// We want to support relative URLs by prefixing with "http://localhost"
Object.defineProperty(global, 'fetch', {
    configurable: true,
    value: vi.fn((url: string, options?: any) => {
        let absoluteUrl = url;
        if (url.startsWith('/')) {
            absoluteUrl = `http://localhost${url}`;
        }
        if (absoluteUrl === 'http://localhost/virtual-turntable/auth/token') {
            return Promise.resolve({
                ok: true,
                json: () => Promise.resolve({ accessToken: 'token123' }),
            });
        }
        if (absoluteUrl === 'http://localhost/virtual-turntable/server/isHost') {
            return Promise.resolve({
                ok: true,
                json: () => Promise.resolve({ isHost: false }),
            });
        }
        if (absoluteUrl === 'http://localhost/virtual-turntable/server/host') {
            return Promise.resolve({
                ok: true,
                json: () => Promise.resolve({ hostUserID: 'host1' }),
            });
        }
        return Promise.resolve({ ok: false });
    }),
});

// --- Make window.location writable ---
Object.defineProperty(window, 'location', {
    writable: true,
    value: { href: '' },
});

beforeEach(() => {
    vi.clearAllMocks();
});

describe('App Component', () => {
    test('renders RemoteController view when user is premium and not host', async () => {
        render(<App />);
        // Wait for the auth token and user profile to be fetched,
        // then expect the RemoteController view to be rendered.
        await waitFor(() => {
            expect(screen.getByTestId('remote-controller')).toBeInTheDocument();
        });
    });

    test('renders VirtualTurntable view when isHost is true', async () => {
        // Override the fetch responses to simulate isHost being true
        (global.fetch as any).mockImplementation((url: string, options?: any) => {
            let absoluteUrl = url;
            if (url.startsWith('/')) {
                absoluteUrl = `http://localhost${url}`;
            }
            if (absoluteUrl === 'http://localhost/virtual-turntable/auth/token') {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({ accessToken: 'token123' }),
                });
            }
            if (absoluteUrl === 'http://localhost/virtual-turntable/server/isHost') {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({ isHost: true }),
                });
            }
            if (absoluteUrl === 'http://localhost/virtual-turntable/server/host') {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({ hostUserID: 'host1' }),
                });
            }
            return Promise.resolve({ ok: false });
        });
        render(<App />);
        await waitFor(() => {
            expect(screen.getByTestId('virtual-turntable')).toBeInTheDocument();
        });
    });

    test('redirects to login when auth token fetch fails', async () => {
        (global.fetch as any).mockImplementation((url: string, options?: any) => {
            let absoluteUrl = url;
            if (url.startsWith('/')) {
                absoluteUrl = `http://localhost${url}`;
            }
            if (absoluteUrl === 'http://localhost/virtual-turntable/auth/token') {
                return Promise.resolve({ ok: false });
            }
            return Promise.resolve({ ok: false });
        });
        render(<App />);
        await waitFor(() => {
            expect(window.location.href).toBe('/virtual-turntable/auth/login');
        });
    });
});
