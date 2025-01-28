import { useCallback, useEffect, useState } from 'react';
import { ColorName, colornames } from 'color-name-list';

import SpotifyPlayer from './Spotify/SpotifyPlayer.ts'
import { Album, Track } from './types/Spotify'

import './styles/App.css'
import SpotifyAPI from './Spotify/SpotifyAPI.ts';

type VirtualTurntableProps = {
    authToken: string;
    isPlaying: boolean;
    setIsPlaying: (playing: boolean) => void;
    currentAlbum: Album | null;
    setCurrentAlbum: (album: Album | null) => void;
    currentTrack: Track | null;
    setCurrentTrack: (track: Track | null) => void;
};

function VirtualTurntable({
    authToken,
    isPlaying, currentAlbum,
    setIsPlaying, setCurrentAlbum, setCurrentTrack,
}: VirtualTurntableProps): JSX.Element {

    const [deviceID, setDeviceID] = useState<string | undefined>(undefined);
    const [isActive, setIsActive] = useState<boolean>(false);

    const [, setPlayer] = useState<SpotifyPlayer | null>(null);

    const [centreLabelSource, setCentreLabelSource] = useState<string | null>(null);
    const [vinylDetails, setVinylDetails] = useState<any>(null);

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
        if (authToken !== '' && deviceID !== undefined) {
            // if (BUILD_MODE !== 'development') {
                handleActivation();
            // }
        }
    }, [authToken, deviceID, handleActivation]);

    useEffect(() => {
        if (!isActive) {
            setCurrentAlbum(null);
            setCurrentTrack(null);
        }
    }, [isActive, setCurrentAlbum, setCurrentTrack]);

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

    if (authToken && authToken !== '') {
        // WEB PLAYBACK

        const dicsClasses = ['disc'];
        if (!isActive) {
            dicsClasses.push('inactive');
        }
        if (isPlaying) {
            dicsClasses.push('spinning');
        }

        return (
            <div
                style={{
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                }}
                onClick={handleActivation}
            >
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
