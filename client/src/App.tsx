import { useEffect, useState } from 'react';

import SpotifyPlayer from './SpotifyPlayer'

import './styles/App.css'

export type Track = {
    name: string;
    album: {
        images: {
            url: string;
        }[];
    },
    artists: {
        name: string;
    }[];
}

function App() {

    const [authToken, setAuthToken] = useState('');

    const [deviceID, setDeviceID] = useState<string | undefined>(undefined);

    const [isPlaying, setIsPlaying] = useState<boolean>(false);
    const [isActive, setIsActive] = useState<boolean>(false);
    const [currentTrack, setCurrentTrack] = useState<Track | null>(null);

    useEffect(() => {

        async function getToken() {
            const response = await fetch('/virtual-turntable/auth/token');
            if (response.ok) {
                const json = await response.json();
                setAuthToken(json.access_token);
            }
        }

        getToken();

    }, []);


    async function handleActivation() {
        if (deviceID !== undefined) {
            fetch('https://api.spotify.com/v1/me/player', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${authToken}`
                },
                body: JSON.stringify({ device_ids: [deviceID] }),
            });
        }
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
                <h1>{currentTrack?.name}</h1>
                <div>
                    <img src='/virtual-turntable/vinyl.svg' className={dicsClasses.join(' ')} alt='Vinyl' />
                </div>
                <SpotifyPlayer
                    authToken={authToken} setDeviceID={setDeviceID}
                    isActive={isActive} isPlaying={isPlaying}
                    setIsPlaying={setIsPlaying} setIsActive={setIsActive} setCurrentTrack={setCurrentTrack}
                />
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
