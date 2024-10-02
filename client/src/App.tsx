import { useEffect, useState } from 'react';

import SpotifyPlayer from './SpotifyPlayer'

import './styles/App.css'

function App() {

    const [authToken, setAuthToken] = useState('');
    const [playing, setPlaying] = useState<boolean>(false);

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

    if (authToken !== '') {
        return (
            <>
                <div>
                    <img src='/virtual-turntable/vinyl.svg' className={!playing ? 'logo' : 'logo spin'} alt='Vinyl' />
                </div>
                <SpotifyPlayer authToken={authToken} setPlaying={setPlaying} />
            </>
        );
    }
    else {
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
