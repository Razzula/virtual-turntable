import { useEffect, useState } from 'react'

import { Track } from './App';

// see https://developer.spotify.com/documentation/web-playback-sdk/reference/

type WebPlaybackPlayer = {
    device_id: string;
};

type WebPlaybackError = {
    message: string;
};

type SpotifyPlayerProps = {
    authToken: string;
    setDeviceID: (player: string) => void;

    isActive: boolean;
    isPlaying: boolean;

    setIsPlaying: (playing: boolean) => void;
    setIsActive: (active: boolean) => void;
    setCurrentTrack: (track: Track | null) => void;
};

function SpotifyPlayer({ authToken, setDeviceID, isActive, isPlaying, setIsPlaying, setIsActive, setCurrentTrack }: SpotifyPlayerProps): JSX.Element {

    const [player, setPlayer] = useState<Spotify.Player | null>(null);

    useEffect(() => {

        // dynamically load Spotify SDK
        const loadSpotifyPlayer = () => {
            return new Promise<void>((resolve, reject) => {
                const script = document.createElement('script');
                script.src = 'https://sdk.scdn.co/spotify-player.js'; // Spotify Web Playback SDK
                script.async = true;

                script.onload = () => {
                    console.log('Spotify SDK loaded successfully.');
                    resolve();
                };

                script.onerror = (error) => {
                    console.error('Failed to load Spotify SDK:', error);
                    reject(new Error('Failed to load Spotify SDK.'));
                };

                document.body.appendChild(script);
            });
        };

        // define functions for Spotify SDK to call
        window.onSpotifyWebPlaybackSDKReady = () => {
            if (player === null) {
                const newPlayer = new Spotify.Player({
                    name: 'Virtual Turntable',
                    getOAuthToken: (cb: (authToken: string) => void) => { cb(authToken); },
                    volume: 0.3
                });

                newPlayer.addListener('ready', ({ device_id }: WebPlaybackPlayer ) => {
                    console.log('Ready with Device ID', device_id);
                    setDeviceID(device_id);
                });
                newPlayer.addListener('not_ready', ({ device_id }: WebPlaybackPlayer ) => {
                    console.log('Device ID has gone offline', device_id);
                });

                newPlayer.addListener('player_state_changed', (state: Spotify.PlaybackState) => {
                    handlePlayerStateChange(state);
                });

                newPlayer.addListener('initialization_error', ({ message }: WebPlaybackError) => {
                    console.error(message);
                });
                newPlayer.addListener('authentication_error', ({ message }: WebPlaybackError) => {
                    console.error(message);
                });
                newPlayer.addListener('account_error', ({ message }: WebPlaybackError) => {
                    console.error(message);
                });

                newPlayer.connect();

                setPlayer(newPlayer);
            }
        };

        // load Spotify SDK
        loadSpotifyPlayer().catch((error) => {
            console.error('Error during SDK loading:', error);
        });

        // cleanup
        return () => {
            if (player !== null) {
                player.removeListener('ready');
                player.removeListener('not_ready');
                player.removeListener('initialization_error');
                player.removeListener('authentication_error');
                player.removeListener('account_error');
                player.disconnect();
                setPlayer(null);
            }
        };

    }, [player]);

    function handleTogglePlay() {
        if (player !== null) {
            player.togglePlay();
        }
    }

    function handlePlayerStateChange(state: Spotify.PlaybackState) {
        // console.log('Player state changed', state);
        if (state) {
            if (state.paused) {
                setIsPlaying(false);
            }
            else {
                setIsPlaying(true);
            }

            setCurrentTrack(state.track_window.current_track);
            setIsActive(state.track_window.current_track !== null);
        }
        else {
            setIsActive(false);
            setCurrentTrack(null);
        }
    }

    function handleNextTrack() {
        if (player !== null) {
            player.nextTrack();
        }
    }

    function handlePreviousTrack() {
        if (player !== null) {
            player.previousTrack();
        }
    }

    return <div>
        <button disabled={!isActive} onClick={handlePreviousTrack}>
            &lt;&lt;
        </button>
        <button disabled={!isActive} onClick={handleTogglePlay}>
            { isPlaying ? 'PAUSE' : 'PLAY' }
        </button>
        <button disabled={!isActive} onClick={handleNextTrack}>
            &gt;&gt;
        </button>
    </div>;

}

export default SpotifyPlayer;
