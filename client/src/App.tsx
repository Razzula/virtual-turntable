import { useCallback, useEffect, useRef, useState } from 'react';

import WebSocketManagerInstance from './WebSocketManager';
import { Album, Track, User } from './types/Spotify'

import './styles/App.css'
import SpotifyAPI from './Spotify/SpotifyAPI';
import VirtualTurntable from './VirtualTurntable';
import RemoteController from './RemoteController';
import SpotifyPlayer from './Spotify/SpotifyPlayer';
import { base64ToBlob } from './utils/blob';

export type Settings = {
    enableMotor: boolean;
    enableRemote: boolean;
    enforceSignature: boolean;
    volume: number;
}

const BUILD_MODE = import.meta.env.MODE;

function App() {

    const [isHostDevice, setIsHostDevice] = useState<boolean>(false);
    const isHostDeviceRef = useRef(isHostDevice);

    const [authToken, setAuthToken] = useState<string | undefined | null>(undefined);
    const [userProfile, setUserProfile] = useState<User | null>(null);
    const [hostUserID, setHostUserID] = useState<string | null>(null);

    const [isPlaying, setIsPlaying] = useState<boolean>(false);

    const [currentAlbum, setCurrentAlbum] = useState<Album | null>(null);
    const [currentTrack, setCurrentTrack] = useState<Track | null>(null);

    const [needToFetchCapture, setNeedToFetchCapture] = useState<'capture' | 'upload' | null>(null);
    const [needToRefreshPlaylist, setNeedToRefreshPlaylist] = useState<boolean>(false);

    const [settings, setSettings] = useState<Settings>({
        enableMotor: true,
        enableRemote: true,
        enforceSignature: false,
        volume: 50,
    });
    const isSettingsUpdateLocal = useRef(false);

    const fetchAuthToken = useCallback(async () => {
        // get auth token
        fetch('/virtual-turntable/auth/token', {
            method: 'GET',
            credentials: 'include',
        })
            .then((response) => {
                if (response.ok) {
                    response.json().then((data) => {
                        setAuthToken(data.accessToken);
                    });
                }
                else {
                    console.error('Failed to get auth token');
                    setAuthToken(null);
                }
            }
            );
    }, []);

    useEffect(() => {
        fetchAuthToken();
    }, [fetchAuthToken]);

    useEffect(() => {
        // resolve host device status
        fetch('/virtual-turntable/server/isHost')
            .then((response) => {
                if (response.ok) {
                    response.json().then((data) => {
                        setIsHostDevice(data?.isHost);
                    });
                }
            }
            );

        // get host ID
        refreshCurrentHostID();
    }, []);

    useEffect(() => {
        if (BUILD_MODE === 'development') {
            // toggle host device status with Ctrl + #
            const handleKeyDown = (e: KeyboardEvent) => {
                if (e.ctrlKey && e.key === '#') {
                    setIsHostDevice((prev) => !prev);
                }
            };
            window.addEventListener('keydown', handleKeyDown);
            return () => {
                window.removeEventListener('keydown', handleKeyDown);
            };
        }
    }, []);

    useEffect(() => {
        if (authToken === null) {
            self.location.href = '/virtual-turntable/auth/login';
        }
        else if (authToken !== undefined) {
            // get current user data
            SpotifyAPI.getOwnProfile(authToken)
                .then((data) => {
                    setUserProfile(data);
                }
                );

            // connect to WebSocket server
            const hostURL = process.env.HOST_NAME || process.env.HOST_URL || 'localhost';
            WebSocketManagerInstance.connect(`wss://${hostURL}/ws`, handleWebSocketMessage);
        }
    }, [authToken]);

    useEffect(() => {
        if (userProfile) {
            if (userProfile.product !== 'premium') {
                console.error('Spotify Premium account required');
            }
        }
    }, [userProfile]);

    useEffect(() => {
        // store isHostDevice in ref, so it can be accessed in WebSocket message handler
        isHostDeviceRef.current = isHostDevice;
    }, [isHostDevice]);

    useEffect(() => {
        if (isHostDevice) { // broadcast to side devices
            WebSocketManagerInstance.send(JSON.stringify({ command: 'playState', value: isPlaying }));
        }
    }, [isPlaying, isHostDevice]);

    useEffect(() => {
        if (isHostDevice) { // broadcast to side devices
            WebSocketManagerInstance.send(JSON.stringify({ command: 'currentTrack', value: currentTrack }));
        }
    }, [currentTrack, isHostDevice]);

    useEffect(() => {
        if (isHostDevice && isSettingsUpdateLocal.current) { // broadcast to side devices
            WebSocketManagerInstance.send(JSON.stringify({ command: 'settings', value: settings }));
        }
    }, [settings, isHostDevice]);

    useEffect(() => {
        if (authToken && currentTrack !== null) {
            // get album info from track
            SpotifyAPI.getAlbum(authToken, currentTrack.album.uri.split(':')[2])
                .then((data: Album) => {
                    setCurrentAlbum(data);
                }
                );
        }
    }, [currentTrack, authToken]);

    function refreshCurrentHostID() {
        fetch('/virtual-turntable/server/host')
            .then((response) => {
                if (response.ok) {
                    response.json().then((data) => {
                        setHostUserID(data.hostUserID);
                    });
                }
            }
            );
    }

    function handleWebSocketMessage(e: MessageEvent) {
        try {
            const message = JSON.parse(e.data);
            console.log('SERVER:', message);

            if (message.command === 'TOKEN') {
                fetchAuthToken();
                return;
            }
            else if (message.command === 'REFRESH_HOST') {
                refreshCurrentHostID();
            }
            else if (message.command === 'settings') {
                isSettingsUpdateLocal.current = false; // origin from server; prevent re-broadcasts
                setSettings(message.value);
            }
            else if (message.command === 'refreshPlaylist') {
                setNeedToRefreshPlaylist(true);
            }

            if (isHostDeviceRef.current) {
                // MAIN
                const player = SpotifyPlayer.getExistingInstance();

                // server commands
                if (message.command === 'playAlbum') {
                    if (authToken !== undefined && authToken !== null) {
                        SpotifyAPI.playAlbum(authToken, message.value);
                        SpotifyAPI.setShuffle(authToken, false);
                    }
                }
                else if (message.command === 'playTrack') {
                    if (authToken !== undefined && authToken !== null) {
                        SpotifyAPI.playTrack(authToken, message.value);
                        SpotifyAPI.setShuffle(authToken, false);
                    }
                }
                else if (message.command === 'playPlaylist') {
                    if (authToken !== undefined && authToken !== null) {
                        SpotifyAPI.playPlaylist(authToken, message.value);
                        SpotifyAPI.setShuffle(authToken, true);
                    }
                }
                else if (message.command === 'capture' || message.command === 'upload') {
                    setNeedToFetchCapture(message.command);
                }

                // side controller commands
                else if (player) {
                    if (message.command === 'playState') {
                        if (message.value === true) {
                            player.play();
                        }
                        else {
                            player.pause();
                        }
                    }
                    else if (message.command === 'playPrevious') {
                        player.previousTrack();
                    }
                    else if (message.command === 'playNext') {
                        player.nextTrack();
                    }
                }
            }
            else {
                // SIDE
                if (message.command === 'playState') {
                    setIsPlaying(message.value);
                }
                else if (message.command === 'currentTrack') {
                    setCurrentTrack(message.value);
                }
            }
        }
        catch (err) {
            console.error('Invalid message:', e.data);
        }

    }

    async function handleUpload(input: File | string) {
        if (typeof input === 'string') {
            // convert Base64 string (from camera) to a Blob
            const blob = base64ToBlob(input);
            await uploadFile(blob);
        }
        else {
            // direct File upload (from file input)
            await uploadFile(input);
        }
        WebSocketManagerInstance.send(JSON.stringify({ command: 'upload' }));
    }

    async function uploadFile(data: File | Blob) {
        const arrayBuffer = await data.arrayBuffer();
        const response = await fetch('/virtual-turntable/server/scan', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/octet-stream',
            },
            body: arrayBuffer,
        });

        const result = await response.json();
        console.log(result);
    }

    if (authToken && authToken !== '') {

        if (isHostDevice) {
            return (
                <VirtualTurntable
                    authToken={authToken} userProfile={userProfile}
                    isPlaying={isPlaying} setIsPlaying={setIsPlaying}
                    currentAlbum={currentAlbum} setCurrentAlbum={setCurrentAlbum}
                    currentTrack={currentTrack} setCurrentTrack={setCurrentTrack}
                    hostSettings={settings} setHostSettings={setSettings} isHostSettingsUpdateLocal={isSettingsUpdateLocal}
                    hostUserID={hostUserID}
                    needToFetchCapture={needToFetchCapture} setNeedToFetchCapture={setNeedToFetchCapture}
                />
            );
        }
        else {
            return (
                <RemoteController
                    authToken={authToken}
                    userProfile={userProfile}
                    isPlaying={isPlaying}
                    currentAlbum={currentAlbum}
                    currentTrack={currentTrack}
                    handleUpload={handleUpload}
                    hostUserID={hostUserID}
                    hostSettings={settings} isHostSettingsUpdateLocal={isSettingsUpdateLocal}
                    needToRefreshPlaylist={needToRefreshPlaylist} setNeedToRefreshPlaylist={setNeedToRefreshPlaylist}
                />
            );
        }

    }
    else {
        // LOGIN
        return (
            <div>
                <h1>
                    <a href='/virtual-turntable/auth/login'>Login with Spotify</a>
                </h1>
            </div>
        );
    }

}

export default App
