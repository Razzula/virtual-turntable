import { useCallback, useEffect, useRef, useState } from 'react';

import WebSocketManagerInstance from './WebSocketManager';
import { Album, Track, User } from './types/Spotify'

import './styles/App.css'
import SpotifyAPI from './Spotify/SpotifyAPI';
import VirtualTurntable from './VirtualTurntable';
import RemoteController from './RemoteController';
import SpotifyPlayer from './Spotify/SpotifyPlayer';

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

    const [settings, setSettings] = useState<Settings>({
        enableMotor: true,
        enableRemote: true,
        enforceSignature: false,
        volume: 50,
    });

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
        fetch('/virtual-turntable/server/clientIP')
            .then((response) => {
                if (response.ok) {
                    response.json().then((data) => {
                        setIsHostDevice(window.location.hostname === data.clientIP);
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
            const hostURL = process.env.HOST_URL || 'localhost';
            WebSocketManagerInstance.connect(`ws://${hostURL}:8491/ws`, handleWebSocketMessage);
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
        if (isHostDevice) { // broadcast to side devices
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
                setSettings(message.value);
            }

            if (isHostDeviceRef.current) {
                // MAIN
                const player = SpotifyPlayer.getExistingInstance();

                // server commands
                if (message.command === 'ALBUM') {
                    SpotifyAPI.playAlbum(message.token, message.value);
                }
                else if (message.command === 'SETTINGS') {
                    console.log(message.value);
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
                    else if (message.command === 'PREVIOUS') {
                        player.previousTrack();
                    }
                    else if (message.command === 'NEXT') {
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

    async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
        const file = e.target.files?.item(0);
        if (file !== undefined && file !== null) {
            await uploadFile(file);
        }
    }

    async function uploadFile(file: File) {
        const arrayBuffer = await file.arrayBuffer();
        const response = await fetch('/virtual-turntable/server/scan', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/octet-stream',
            },
            body: arrayBuffer
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
                    hostSettings={settings} setHostSettings={setSettings}
                    hostUserID={hostUserID}
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
                    handleFileUpload={handleFileUpload}
                    hostUserID={hostUserID}
                    hostSettings={settings}
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
