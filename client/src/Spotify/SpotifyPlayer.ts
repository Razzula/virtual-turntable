import MusicPlayer from '../IMusicPlayer';

type WebPlaybackPlayer = {
    device_id: string;
};

type WebPlaybackError = {
    message: string;
};

const BUILD_MODE = import.meta.env.MODE;

export class SpotifyPlayer extends MusicPlayer {
    // see https://developer.spotify.com/documentation/web-playback-sdk/reference/

    private player: Spotify.Player | null = null;

    protected constructor(authToken: string, setDeviceID: (player: string) => void, handlePlayerStateChange: (state: Spotify.PlaybackState) => void) {
        super();
        console.log('Creating Spotify Player instance');

        const loadSpotifyPlayer = () => {
            return new Promise<void>((resolve, reject) => {
                const script = document.createElement('script');
                script.src = 'https://sdk.scdn.co/spotify-player.js'; // Spotify Web Playback SDK
                script.async = true;

                script.onload = () => {
                    // console.log('Spotify SDK loaded successfully.');
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
            const newPlayer = new Spotify.Player({
                name: 'Virtual Turntable',
                getOAuthToken: (cb: (authToken: string) => void) => { cb(authToken); },
                volume: 0.5
            });

            // state management
            newPlayer.addListener('ready', ({ device_id }: WebPlaybackPlayer ) => {
                if (BUILD_MODE === 'development') {
                    console.log('Ready with Device ID', device_id);
                }
                setDeviceID(device_id);
            });
            newPlayer.addListener('not_ready', ({ device_id }: WebPlaybackPlayer ) => {
                console.log('Device ID has gone offline', device_id);
            });

            newPlayer.addListener('player_state_changed', (state: Spotify.PlaybackState) => {
                handlePlayerStateChange(state);
            });

            // error handlers
            newPlayer.addListener('autoplay_failed', () => {
                console.error('Autoplay failed. This may be due to DRM issues or autoplay restrictions.');
            });
            newPlayer.addListener('initialization_error', ({ message }: WebPlaybackError) => {
                console.error('Initialisation error:', message);
            });
            newPlayer.addListener('authentication_error', ({ message }: WebPlaybackError) => {
                console.error('Authentication error:', message);
            });
            newPlayer.addListener('account_error', ({ message }: WebPlaybackError) => {
                console.error('Account error:', message);
            });

            newPlayer.connect();
            this.player = newPlayer;
        };

        // load Spotify SDK
        loadSpotifyPlayer().catch((error) => {
            console.error('Error during SDK loading:', error);
        });
    }

    public togglePlay() {
        this.player?.togglePlay();
    }

    public play() {
        this.player?.resume();
    }

    public pause() {
        this.player?.pause();
    }

    public nextTrack() {
        this.player?.nextTrack();
    }

    public previousTrack() {
        this.player?.previousTrack();
    }

}
export default SpotifyPlayer;
