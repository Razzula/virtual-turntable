import { useCallback, useEffect, useState } from 'react';
// import colornames from 'colornames';
import { colornames } from 'color-name-list';

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
                // debugger;
                if (metadata?.colour) {
                    metadata.colour = colornames.find((colour: any) => colour.name.toLowerCase() === metadata.colour.toLowerCase())?.hex;
                }
                console.log(metadata);
                setVinylDetails(metadata);
            } catch (error) {
                console.error('Error fetching label:', error);
                setCentreLabelSource(null); // prevent stale image
            }
        };

        setCentreLabelSource(null); // clear previous label
        setVinylDetails(null);
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
                                    opacity: 0.5, // Adjust transparency
                                    pointerEvents: "none", // Makes the overlay non-interactive
                                    borderRadius: '50%',
                                }}
                            />
                        }

                        {/* VINYL TEXTURE */}
                        <img src='/virtual-turntable/vinyl.png'
                            style={{
                                position: "absolute",
                                top: '50%',
                                left: '50%',
                                transform: 'translate(-50%, -50%)',
                                width: 400,
                                height: 400,

                                objectFit: "cover",
                                mixBlendMode: vinylDetails?.colour ? "darken" : "lighten", // Adjust as needed
                                opacity: 0.4, // Adjust transparency
                                pointerEvents: "none", // Makes the overlay non-interactive
                                borderRadius: '50%',
                            }}
                        />

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
    </svg>
);

<Vinyl colour="#3498db" />; // Pass the desired colour dynamically


export default App
