import { useCallback, useEffect, useState } from 'react';

import SpotifyPlayer from './SpotifyPlayer'
import WebSocketManagerInstance from './WebSocketManager'

import './styles/App.css'
import SpotifyAPI from './SpotifyAPI';

export type Track = {
    name: string;
    album: {
        uri: string;
    },
    artists: {
        name: string;
    }[];
}

type Album = {
    album_type: string;
    artists: {
        name: string;
    }[];
    images: {
        url: string;
        height: number;
        width: number;
    }[];
    label : string;
    name: string;
    release_date: string;
}

const BUILD_MODE = import.meta.env.MODE;

function App() {

    const [authToken, setAuthToken] = useState('');

    const [deviceID, setDeviceID] = useState<string | undefined>(undefined);

    const [isPlaying, setIsPlaying] = useState<boolean>(false);
    const [isActive, setIsActive] = useState<boolean>(false);

    const [currentAlbum, setCurrentAlbum] = useState<Album | null>(null);
    const [currentTrack, setCurrentTrack] = useState<Track | null>(null);

    const handleActivation = useCallback(async () => {
        if (deviceID !== undefined) {
            if (BUILD_MODE !== 'development') {
                SpotifyAPI.setDevice(authToken, deviceID);
            }
        }
        else {
            console.warn('Cannot activate player without device ID');
        }
    }, [authToken, deviceID]);

    useEffect(() => {

        async function getToken() {
            const response = await fetch('/virtual-turntable/auth/token');
            if (response.ok) {
                const json = await response.json();
                setAuthToken(json.access_token);
            }
        }

        getToken();

        WebSocketManagerInstance.connect('ws://localhost:8491/ws', handleWebSocketMessage);

    }, []);

    useEffect(() => {
        if (authToken !== '' && deviceID !== undefined) {
            handleActivation();
        }
    }, [authToken, deviceID, handleActivation]);

    useEffect(() => {
        if (!isActive) {
            setCurrentAlbum(null);
            setCurrentTrack(null);
        }
    }, [isActive]);

    useEffect(() => {
        if (currentTrack !== null) {
            SpotifyAPI.getAlbum(authToken, currentTrack.album.uri.split(':')[2])
                .then((data: Album) => {
                    setCurrentAlbum(data);
                });
        }
    }, [currentTrack, authToken]);

    function handleWebSocketMessage(e: MessageEvent) {
        const message = JSON.parse(e.data);
        console.log('SERVER:', message);

        if (message.command === 'ALBUM') {
            // SpotifyAPI.getAlbum(message.token, message.value)
            //     .then((data: Album) => {
            //         setCurrentAlbum(data);
            //     })
            SpotifyAPI.playAlbum(message.token, message.value);
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

    if (authToken !== '') {
        // WEB PLAYBACK

        const dicsClasses = ['disc'];
        if (!isActive) {
            dicsClasses.push('inactive');
        }
        if (isPlaying) {
            dicsClasses.push('spinning');
        }

        return (
            <>
                { !isActive &&
                    <button onClick={handleActivation}>ACTIVATE</button>
                }

                <h1>{currentAlbum?.name}</h1>
                { currentAlbum !== null &&
                    <img className='albumArt' src={currentAlbum.images[0].url} alt='Album Cover' />
                }
                <h2>{currentTrack?.name}</h2>

                <div>
                    <img src='/virtual-turntable/vinyl.svg' className={dicsClasses.join(' ')} alt='Vinyl' />
                </div>

                <SpotifyPlayer
                    authToken={authToken} setDeviceID={setDeviceID}
                    isActive={isActive} isPlaying={isPlaying}
                    setIsPlaying={setIsPlaying} setIsActive={setIsActive} setCurrentTrack={setCurrentTrack}
                />

                <div>
                    <button onClick={() => WebSocketManagerInstance.send('PING!')}>PING SERVER</button>
                </div>
                <div>
                    <input type="file" accept="image/*" onChange={handleFileUpload} />
                </div>
            </>
        );
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
