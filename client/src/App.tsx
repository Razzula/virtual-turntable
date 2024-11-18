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
    id: string;
    album_type: string;
    artists: {
        name: string;
    }[];
    images: {
        url: string;
        height: number;
        width: number;
    }[];
    label: string;
    name: string;
    release_date: string;
}

const BUILD_MODE = import.meta.env.MODE;

function App() {

    const [authToken, setAuthToken] = useState<string | undefined | null>(undefined);

    const [deviceID, setDeviceID] = useState<string | undefined>(undefined);

    const [isPlaying, setIsPlaying] = useState<boolean>(false);
    const [isActive, setIsActive] = useState<boolean>(false);

    const [currentAlbum, setCurrentAlbum] = useState<Album | null>(null);
    const [currentTrack, setCurrentTrack] = useState<Track | null>(null);

    const [centreLabelSource, setCentreLabelSource] = useState<string | null>(null);
    const [vinylDetails, setVinylDetails] = useState<any>(null);

    const handleActivation = useCallback(async () => {
        if (authToken) {
            if (deviceID !== undefined) {
                if (BUILD_MODE !== 'development') {
                    SpotifyAPI.setDevice(authToken, deviceID);
                }
            }
            else {
                console.warn('Cannot activate player without device ID');
            }
        }
    }, [authToken, deviceID]);

    useEffect(() => {
        if (authToken === null) {
            self.location.href = '/virtual-turntable/auth/login';
        }
    }, [authToken]);

    useEffect(() => {

        async function getToken() {
            const response = await fetch('/virtual-turntable/auth/token');
            if (response.ok) {
                const json = await response.json();
                setAuthToken(json.access_token);
            }
            else {
                setAuthToken(null);
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
        if (authToken && currentTrack !== null) {
            SpotifyAPI.getAlbum(authToken, currentTrack.album.uri.split(':')[2])
                .then((data: Album) => {
                    setCurrentAlbum(data);
                });
        }
    }, [currentTrack, authToken]);

    useEffect(() => {
        // FETCH CENTRE LABEL ON ALBUM CHANGE
        const fetchLabel = async () => {
            if (!currentAlbum?.id) return;

            try {
                // HANDLED BY SERVER
                const response = await fetch('/virtual-turntable/server/centreLabel', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        albumID: currentAlbum.id,
                        albumName: currentAlbum.name,
                        artistName: currentAlbum.artists[0].name,
                        year: currentAlbum.release_date.split('-')[0],
                    }),
                });

                if (!response.ok) {
                    throw new Error('Failed to fetch centre label');
                }

                const result = await response.json();

                // store image as blob URL, to display in <img>
                const base64Image = result.imageData;
                const binary = atob(base64Image);
                const array = new Uint8Array(binary.length);
                for (let i = 0; i < binary.length; i++) {
                    array[i] = binary.charCodeAt(i);
                }

                const blob = new Blob([array], { type: 'image/png' });
                const url = URL.createObjectURL(blob);
                setCentreLabelSource(url);

                // optional metadata
                const metadata = result.metadata;
                setVinylDetails(metadata);
            } catch (error) {
                console.error('Error fetching label:', error);
                setCentreLabelSource(null); // prevent stale image
            }
        };

        setCentreLabelSource(null); // clear previous label
        fetchLabel();

        return () => {
            if (centreLabelSource) {
                URL.revokeObjectURL(centreLabelSource); // Clean up blob URL
            }
        };
    }, [currentAlbum?.id]);

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
                {!isActive &&
                    <button onClick={handleActivation}>ACTIVATE</button>
                }

                <h1>{currentAlbum?.name}</h1>
                {currentAlbum !== null &&
                    <img className='albumArt' src={currentAlbum.images[0].url} alt='Album Cover' />
                }
                <h2>{currentTrack?.name}</h2>

                <div style={{
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                }}>
                    {/* SPINNING VINYL RENDER */}
                    <div className={dicsClasses.join(' ')}
                        style={{
                            position: 'relative',
                        }}
                    >
                        {/* PLAIN VINYL */}
                        <Vinyl colour={vinylDetails?.colour || '#000000'} />

                        {/* MARBLE TEXTURE */}
                        { vinylDetails?.marble &&
                            <img src='/virtual-turntable/marble.webp'
                                style={{
                                    position: "absolute",
                                    top: '50%',
                                    left: '50%',
                                    transform: 'translate(-50%, -50%)',
                                    width: 394,
                                    height: 394,

                                    objectFit: "cover",
                                    mixBlendMode: "multiply", // Adjust as needed
                                    opacity: 0.6, // Adjust transparency
                                    pointerEvents: "none", // Makes the overlay non-interactive
                                    borderRadius: '50%',
                                }}
                            />
                        }

                        {/* CENTRE LABEL */}
                        {centreLabelSource &&
                            <img src={centreLabelSource}
                                style={{
                                    position: 'absolute',
                                    top: '50%',
                                    left: '50%',
                                    transform: 'translate(-50%, -50%)',
                                    borderRadius: '50%',
                                    zIndex: 1,
                                    width: 180,
                                    height: 180,
                                }}
                            />
                        }
                    </div>
                </div>

                { authToken &&
                    <SpotifyPlayer
                        authToken={authToken} setDeviceID={setDeviceID}
                        isActive={isActive} isPlaying={isPlaying}
                        setIsPlaying={setIsPlaying} setIsActive={setIsActive} setCurrentTrack={setCurrentTrack}
                    />
                }

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

const Vinyl = ({ colour }: { colour: string }) => (
    <svg
        xmlns="http://www.w3.org/1999/xlink" x="0px" y="0px"
        viewBox="0 0 488.2 488.2"
        style={{ width: "100%", height: "100%" }}
    >
        <circle fill={colour} cx="244.1" cy="244.2" r="244"/>
        <circle fill='#ffffff' cx="244.1" cy="244.2" r="104.8"/>
        <circle fill={colour} cx="244.1" cy="244.2" r="29.6"/>
        <g>
            <path fill='#ffffff' d="M244.1,448.2c-112.8,0-204-91.2-204-204c0-4,3.2-8,8-8c4,0,8,3.2,8,8c-0.8,104,84,188.8,188,188.8
                c4,0,8,3.2,8,8C252.1,445,248.1,448.2,244.1,448.2z"
            />
            <path fill='#ffffff' d="M440.9,252.2c-4,0-8-3.2-8-8c0-104-84.8-188.8-188.8-188.8c-4,0-8-3.2-8-8c0-4,3.2-8,8-8
                c112.8,0,204,92,204,204C448.1,248.2,444.9,252.2,440.9,252.2z"
            />
            <path fill='#ffffff' d="M244.1,401c-86.4,0-156.8-70.4-156.8-156.8c0-4,3.2-8,8-8c4,0,8,3.2,8,8
                c0,77.6,63.2,141.6,141.6,141.6c4,0,8,3.2,8,8C252.1,397.8,248.1,401,244.1,401z"
            />
            <path fill='#ffffff' d="M392.9,252.2c-4,0-8-3.2-8-8c0-77.6-63.2-141.6-141.6-141.6c-4,0-8-3.2-8-8c0-4,3.2-8,8-8
                c86.4,0,156.8,70.4,156.8,156.8C400.9,248.2,397.7,252.2,392.9,252.2z"
            />
        </g>
    </svg>
);

<Vinyl colour="#3498db" />; // Pass the desired colour dynamically


export default App
