import { useEffect, useRef, useState } from 'react';

import WebSocketManagerInstance from './WebSocketManager';
import { Album, Track } from './types/Spotify'

import './styles/App.css'
import SpotifyAPI from './Spotify/SpotifyAPI';
import VirtualTurntable from './VirtualTurntable';
import RemoteController from './RemoteController';
import SpotifyPlayer from './Spotify/SpotifyPlayer';

function App() {

    const [isHostDevice, setIsHostDevice] = useState<boolean>(false);
    const isHostDeviceRef = useRef(isHostDevice);

    const [authToken, setAuthToken] = useState<string | undefined | null>(undefined);

    const [isPlaying, setIsPlaying] = useState<boolean>(false);

    const [currentAlbum, setCurrentAlbum] = useState<Album | null>(null);
    const [currentTrack, setCurrentTrack] = useState<Track | null>(null);

    useEffect(() => {
        // get auth token
        fetch('/virtual-turntable/auth/token')
            .then((response) => {
                if (response.ok) {
                    response.json().then((data) => {
                        setAuthToken(data.access_token);
                    });
                }
                else {
                    setAuthToken(null);
                }
            }
        );

        fetch('/virtual-turntable/server/clientIP')
            .then((response) => {
                if (response.ok) {
                    response.json().then((data) => {
                        const isHostDevice = window.location.hostname === data.clientIP;
                        setIsHostDevice(isHostDevice);

                        // connect to WebSocket server
                        const hostURL = process.env.HOST_URL || 'localhost';
                        WebSocketManagerInstance.connect(`ws://${hostURL}:8491/ws/${isHostDevice ? 'main' : 'side'}`, handleWebSocketMessage);
                    });
                }
            }
        );
    }, []);

    useEffect(() => {
        if (authToken === null) {
            self.location.href = '/virtual-turntable/auth/login';
        }
    }, [authToken]);

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
        if (authToken && currentTrack !== null) {
            // get album info from track
            SpotifyAPI.getAlbum(authToken, currentTrack.album.uri.split(':')[2])
                .then((data: Album) => {
                    setCurrentAlbum(data);
                }
            );
        }
    }, [currentTrack, authToken]);

    function handleWebSocketMessage(e: MessageEvent) {
        try {
            const message = JSON.parse(e.data);
            console.log('SERVER:', message);

            if (isHostDeviceRef.current) {
                // MAIN
                const player = SpotifyPlayer.getExistingInstance();

                // server commands
                if (message.command === 'ALBUM') {
                    SpotifyAPI.playAlbum(message.token, message.value);
                }

                // side controller commands
                else if (player) {
                    if (message.command === 'PLAY') {
                        player.play();
                    }
                    else if (message.command === 'PAUSE') {
                        player.pause();
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
                <div>
                    <VirtualTurntable
                        authToken={authToken}
                        isPlaying={isPlaying} setIsPlaying={setIsPlaying}
                        currentAlbum={currentAlbum} setCurrentAlbum={setCurrentAlbum}
                        currentTrack={currentTrack} setCurrentTrack={setCurrentTrack}
                    />
                    {/* <button onClick={() => WebSocketManagerInstance.send('PING!')}>PING SERVER</button> */}
                </div>
            );
        }
        else {
            return (
                <div>
                    <RemoteController
                        authToken={authToken}
                        isPlaying={isPlaying}
                        currentAlbum={currentAlbum}
                        currentTrack={currentTrack}
                        handleFileUpload={handleFileUpload}
                        // webSocketManagerInstance={WebSocketManagerInstance}
                    />
                </div>
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
