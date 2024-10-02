import { useState } from 'react';

import SpotifyPlayer from './SpotifyPlayer'

import './styles/App.css'

function App() {

    const [playing, setPlaying] = useState<boolean>(false);

    return (
        <>
            <div>
                <img src='/virtual-turntable/vinyl.svg' className={!playing ? "logo" : "logo spin"} alt="React logo" />
            </div>
            <SpotifyPlayer setPlaying={setPlaying} />
        </>
    )
}

export default App
