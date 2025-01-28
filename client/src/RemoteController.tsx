import { Album, Track } from './types/Spotify.ts'

import './styles/App.css'
import WebSocketManagerInstance from './WebSocketManager';

type RemoteControllerProps = {
    authToken: string;
    isPlaying: boolean;
    currentAlbum: Album | null;
    currentTrack: Track | null;
    handleFileUpload: (event: React.ChangeEvent<HTMLInputElement>) => void;
    // webSocketManagerInstance: typeof WebSocketManagerInstance;
};

function RemoteController({
    authToken,
    isPlaying, currentAlbum, currentTrack,
    handleFileUpload,
    // webSocketManagerInstance,
}: RemoteControllerProps): JSX.Element {


    if (authToken && authToken !== '') {
        // CONTROLLER
        return (
            <div>
                <h1>{currentAlbum?.name}</h1>
                {currentAlbum !== null &&
                    <img className='albumArt' src={currentAlbum.images[0].url} alt='Album Cover' />
                }
                <h2>{currentTrack?.name}</h2>

                <button onClick={() => WebSocketManagerInstance.send(JSON.stringify({command: 'PREVIOUS'}))}>PREV</button>
                    <button onClick={() => WebSocketManagerInstance.send(JSON.stringify({command: isPlaying ? 'PAUSE' : 'PLAY'}))}>
                        { isPlaying ? 'PAUSE' : 'PLAY' }
                    </button>
                <button onClick={() => WebSocketManagerInstance.send(JSON.stringify({command: 'NEXT'}))}>NEXT</button>

                <div>
                    <input type="file" accept="image/*" onChange={handleFileUpload} />
                </div>
            </div>
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

export default RemoteController
