import { useCallback, useEffect, useState } from 'react';
import { ColorName, colornames } from 'color-name-list';

import SpotifyPlayer from './Spotify/SpotifyPlayer.ts'
import { Album, Track, User } from './types/Spotify'

import './styles/App.css'
import SpotifyAPI from './Spotify/SpotifyAPI.ts';
import WebSocketManagerInstance from './WebSocketManager.ts';
import { Settings } from './App.tsx';

type VirtualTurntableProps = {
    authToken: string;
    userProfile: User | null;
    isPlaying: boolean;
    setIsPlaying: (playing: boolean) => void;
    currentAlbum: Album | null;
    setCurrentAlbum: (album: Album | null) => void;
    currentTrack: Track | null;
    setCurrentTrack: (track: Track | null) => void;
    hostSettings: Settings;
    setHostSettings: (settings: Settings) => void;
    hostUserID: string | null;
};

type ClientSettings = {
    baseplateWidth: number;
    baseplateHeight: number;
    vinylDiamater: number;
    vinylOffset: number;
    plateZoom: number;
}

const BUILD_MODE = import.meta.env.MODE;

function VirtualTurntable({
    authToken,
    userProfile,
    isPlaying, currentAlbum,
    setIsPlaying, setCurrentAlbum, setCurrentTrack,
    hostSettings, setHostSettings,
    hostUserID,
}: VirtualTurntableProps): JSX.Element {

    const [deviceID, setDeviceID] = useState<string | undefined>(undefined);
    const [isActive, setIsActive] = useState<boolean>(false);

    const [, setPlayer] = useState<SpotifyPlayer | null>(null);

    const [centreLabelSource, setCentreLabelSource] = useState<string | null>(null);
    const [vinylDetails, setVinylDetails] = useState<any>(null);

    const [mouseActive, setMouseActive] = useState(false);
    const [showSettings, setShowSettings] = useState(false);

    const [clientSettings, setClientSettings] = useState<ClientSettings>({
        plateZoom: 50,
        baseplateWidth: 28.5,
        baseplateHeight: 13,
        vinylDiamater: 30,
        vinylOffset: 10,
    });

    const vinylCentre = clientSettings.vinylOffset / clientSettings.baseplateWidth;

    const plateZoomBounds = { min: 10, max: 100 };

    useEffect(() => {
        document.body.className = 'projected';
    }, []);

    useEffect(() => {
        // MOUSE MOVEMENT LISTENER
        let timeout: NodeJS.Timeout;

        const handleMouseMove = () => {
            setMouseActive(true);

            // reset the timer to hide buttons after 3 seconds of no movement
            clearTimeout(timeout);
            timeout = setTimeout(() => {
                setMouseActive(false);
            }, 5000);
        };

        window.addEventListener('mousemove', handleMouseMove);

        return () => {
            window.removeEventListener('mousemove', handleMouseMove);
            clearTimeout(timeout);
        };
    }, []);

    useEffect(() => {
        // CTRL+SCROLL ZOOM LISTENER
        const handleWheel = (e: WheelEvent) => {
            e.preventDefault(); // prevent default page zoom

            setClientSettings((prev) => ({
                ...prev,
                plateZoom: Math.min( // overflow clamp
                    plateZoomBounds.max,
                    Math.max( // underflow clamp
                        plateZoomBounds.min,
                        prev.plateZoom - Math.sign(e.deltaY) * 5 // delta 5%
                    )
                )
            }));
        };

        window.addEventListener('wheel', handleWheel, { passive: false });

        return () => {
            window.removeEventListener('wheel', handleWheel);
        };
    }, []);

    useEffect(() => {
        function handlePlayerStateChange(state: Spotify.PlaybackState) {
            if (state) {
                if (state.paused) {
                    setIsPlaying(false);
                }
                else {
                    setIsPlaying(true);
                }
                setCurrentTrack(state.track_window.current_track);
                setIsActive(state.track_window.current_track !== null);
            }
            else {
                setIsActive(false);
                setCurrentTrack(null);
            }
        }
        setPlayer(SpotifyPlayer.getInstance(authToken, setDeviceID, handlePlayerStateChange));
    }, [authToken, setCurrentTrack, setDeviceID, setIsPlaying]);

    const handleActivation = useCallback(async () => {
        if (authToken) {
            if (deviceID !== undefined) {
                SpotifyAPI.connect(authToken, deviceID);
            }
            else {
                console.warn('Cannot activate player without device ID');
            }
        }
    }, [authToken, deviceID]);

    useEffect(() => {
        if (hostUserID && userProfile?.id) {
            if (hostUserID !== userProfile.id) {
                console.log('erere');
                setIsActive(false);
            }
        }
    }, [hostUserID, userProfile?.id])

    useEffect(() => {
        if (authToken !== '' && deviceID !== undefined) {
            if (BUILD_MODE !== 'development') {
                handleActivation();
            }
        }
    }, [authToken, deviceID, handleActivation]);

    useEffect(() => {
        if (!isActive) {
            setCurrentAlbum(null);
            setCurrentTrack(null);
        }
    }, [isActive, setCurrentAlbum, setCurrentTrack]);

    useEffect(() => {
        WebSocketManagerInstance.send(JSON.stringify({ command: 'settings', value: hostSettings }));
    }, [hostSettings]);

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
                if (metadata?.colour) {
                    metadata.colour = colornames.find((colour: ColorName) => colour.name.toLowerCase() === metadata.colour.toLowerCase())?.hex;
                }
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

    function toggleSettingsDisplay(event: React.MouseEvent<HTMLButtonElement>) {
        event.stopPropagation();
        setShowSettings(!showSettings);
    }

    function updateHostSettings(setting: string, value: any) {
        setHostSettings((prevSettings) => ({
            ...prevSettings,
            [setting]: value,
        }));
    }

    function updateClientSettings(setting: string, value: any) {
        setClientSettings((prevSettings) => ({
            ...prevSettings,
            [setting]: value,
        }));
    }

    const showInteractive = mouseActive || showSettings;

    if (userProfile !== null && userProfile?.product !== 'premium') {
        return (
            <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                height: '100vh',
                width: '100vw',
                overflow: 'hidden',
            }}
            >
                <div className='plate'
                    style={{
                        width: `${clientSettings.plateZoom}vw`,
                        height: `${clientSettings.plateZoom / clientSettings.baseplateWidth * clientSettings.baseplateHeight}vw`,
                    }}
                >
                    <div className='error'
                        style={{
                            margin: 0,
                            padding: 0,
                            width: '100%',
                            height: '100%',
                        }}
                    >
                            <h1>Uh, oh!</h1>
                            <img className='errorImg' src='/virtual-turntable/vinyl-smashed.png' alt='Error' height={150} />
                            <h2>Spotify Premium required.</h2>
                            <p>Your account does not have a Premium subscription, which is required to use playback in this service.</p>
                            <p>
                                Spotify Premium lets you play any track, podcast episode or audiobook, ad-free and with better audio quality.
                                Go to <a href='https://www.spotify.com/premium'>spotify.com/premium</a> to try it for free.
                            </p>
                    </div>
                </div>
            </div>
        );
    }
    else if (authToken && authToken !== '') {
        // WEB PLAYBACK

        const dicsClasses = ['disc'];
        if (!isActive) {
            dicsClasses.push('inactive');
        }
        if (isPlaying) {
            dicsClasses.push('spinning');
        }

        return (
            <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                height: '100vh',
                width: '100vw',
                overflow: 'hidden',
            }}
                onClick={() => setShowSettings(false)}
            >
                <div className={`plate ${showInteractive ? 'showOutline' : ''}`}
                    style={{
                        width: `${clientSettings.plateZoom}vw`,
                        height: `${clientSettings.plateZoom / clientSettings.baseplateWidth * clientSettings.baseplateHeight}vw`,
                    }}
                >
                    <div className='vinyl'
                        style={{
                            position: 'relative',
                            left: `${(-0.5 + vinylCentre) * 100}%`,

                            height: `${clientSettings.plateZoom / clientSettings.baseplateWidth * clientSettings.vinylDiamater}vw`,
                            width: `${clientSettings.plateZoom / clientSettings.baseplateWidth * clientSettings.vinylDiamater}vw`,
                            flexShrink: 0,

                            display: 'flex',
                            justifyContent: 'center',
                            alignItems: 'center',
                            cursor: 'pointer',
                            // border: '1px solid #ff00ff',
                        }}
                        onClick={handleActivation}
                    >
                        {/* SPINNING VINYL RENDER */}
                        <div className={dicsClasses.join(' ')}
                            style={{
                                position: 'relative',
                                width: '100%',
                                height: '100%',
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
                                        width: '100%',
                                        height: '100%',

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
                                    width: '100%',
                                    height: '100%',

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
                                        width: '43%',
                                        height: '43%',
                                    }}
                                />
                            }
                        </div>
                    </div>

                    <div className='topRight'>
                    <a href={userProfile?.external_urls.spotify} target='_blank' rel='noreferrer'>
                            <img className='userImage'
                                src={userProfile?.images?.[0].url || 'https://i.scdn.co/image/ab676161000051747baf6a3e4e70248079e48c5a'} alt='User Profile'
                                style={{
                                    width: `${128 * (clientSettings.plateZoom / 100)}px`,
                                    height: `${128 * (clientSettings.plateZoom / 100)}px`,
                                }}
                            />
                        </a>
                    </div>

                    <div className='bottomRight column'>
                        <p
                            style={{
                                fontSize: `${24 * (clientSettings.plateZoom / 100)}px`,
                            }}
                        >
                            Powered by
                        </p>
                        <a href='https://www.spotify.com/' target='_blank' rel='noreferrer'>
                            <img className='brandImage'
                                src='https://storage.googleapis.com/pr-newsroom-wp/1/2023/05/Spotify_Full_Logo_RGB_Green.png' alt='Spotify Logo'
                                style={{
                                    width: `${200 * (clientSettings.plateZoom / 100)}px`,
                                }}
                            />
                        </a>
                        <a href='https://www.discogs.com/' target='_blank' rel='noreferrer'>
                            <img className='brandImage'
                                src='https://www.discogs.com/images/discogs-white.png' alt='Discogs Logo'
                                style={{
                                    width: `${200 * (clientSettings.plateZoom / 100)}px`,
                                }}
                            />
                        </a>
                    </div>

                </div>

                { showInteractive &&
                    <div className='floating'>
                            <div className='row container' onClick={(e) => e.stopPropagation()}>
                                <img src='/virtual-turntable/icons/zoomOut.svg' alt='-' />
                                <input type='range' min={plateZoomBounds.min} max={plateZoomBounds.max}
                                    value={clientSettings.plateZoom}
                                    onChange={(e) => updateClientSettings('plateZoom', parseInt(e.target.value))}
                                />
                                <img src='/virtual-turntable/icons/zoomIn.svg' alt='+' />

                                <button onClick={toggleSettingsDisplay}>
                                    <img src='/virtual-turntable/icons/settings.svg' alt='Settings' />
                                </button>
                        </div>

                        { showSettings &&
                            <div className='container' onClick={(e) => e.stopPropagation()}>
                                <div className='row'>
                                    Baseplate
                                    <input type='number' value={clientSettings.baseplateWidth} onChange={(e) => updateClientSettings('baseplateWidth', parseFloat(e.target.value))} />
                                    x
                                    <input type='number' value={clientSettings.baseplateHeight} onChange={(e) => updateClientSettings('baseplateHeight', parseFloat(e.target.value))} />
                                </div>
                                <div className='row'>
                                    Vinyl Diameter
                                    <input type='number' value={clientSettings.vinylDiamater} onChange={(e) => updateClientSettings('vinylDiamater', parseFloat(e.target.value))} />
                                </div>
                                <div className='row'>
                                    Vinyl Position
                                    <input type='number' value={clientSettings.vinylOffset}
                                        onChange={(e) => updateClientSettings('vinylOffset', Math.min(clientSettings.baseplateWidth, Math.max(0, parseFloat(e.target.value))))}
                                    />
                                </div>
                            </div>
                        }
                        { showSettings &&
                            <div className='container' onClick={(e) => e.stopPropagation()}>
                                <div className='row'>
                                    <button className={`toggle ${hostSettings.enableMotor ? 'active' : 'inactive'}`}
                                        onClick={() => updateHostSettings('enableMotor', !hostSettings.enableMotor)}
                                    >
                                        <img src='/virtual-turntable/icons/motor.svg' alt='Motor' />
                                    </button>
                                    <button className={`toggle ${hostSettings.enableRemote ? 'active' : 'inactive'}`}
                                        onClick={() => updateHostSettings('enableRemote', !hostSettings.enableRemote)}
                                    >
                                        <img src='/virtual-turntable/icons/remote.svg' alt='Remote Control' />
                                    </button>
                                    <button className={`toggle ${hostSettings.enforceSignature ? 'active' : 'inactive'}`}
                                        onClick={() => updateHostSettings('enforceSignature', !hostSettings.enforceSignature)}
                                        disabled={!hostSettings.enableRemote}
                                    >
                                        <img src='/virtual-turntable/icons/signature.svg' alt='Remote Control' />
                                    </button>
                                    <a href='/virtual-turntable/auth/logout'>
                                        <button>
                                            <img src='/virtual-turntable/icons/logout.svg' alt='Signout' />
                                        </button>
                                    </a>
                                </div>
                            </div>
                        }
                    </div>
                }

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

export default VirtualTurntable
