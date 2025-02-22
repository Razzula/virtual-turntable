import { Album, Track, User } from './types/Spotify.ts'

import './styles/App.css'
import WebSocketManagerInstance from './WebSocketManager';
import React, { useEffect, useState } from 'react';
import SpotifyAPI from './Spotify/SpotifyAPI.ts';
import { Settings } from './App.tsx';
import { Tooltip, TooltipContent, TooltipTrigger } from './common/Tooltip.tsx';
import { Dialogue } from './common/Dialogue';
import { DialogueContent } from './common/Dialogue';
import WebcamCapture from './common/WebcamCapture.tsx';

type RemoteControllerProps = {
    authToken: string;
    userProfile: User | null;
    isPlaying: boolean;
    currentAlbum: Album | null;
    currentTrack: Track | null;
    handleUpload: (input: File | string) => void;
    hostUserID: string | null;
    hostSettings: Settings;
    isHostSettingsUpdateLocal: React.MutableRefObject<boolean>;
};

function RemoteController({
    authToken,
    userProfile,
    isPlaying, currentAlbum, currentTrack,
    handleUpload,
    hostUserID,
    hostSettings, isHostSettingsUpdateLocal,
}: RemoteControllerProps): JSX.Element {

    const [libraryPlaylistID, setLibraryPlaylistID] = useState<string | null>(null);
    const [library, setLibrary] = useState<Album[]>([]);

    const [hostUserProfile, setHostUserProfile] = useState<User | null>(null);

    const [volume, setVolume] = useState<number>(hostSettings.volume);

    const [isScannerOpen, setIsScannerOpen] = useState(false);

    useEffect(() => {
        document.body.className = 'default';
    }, []);

    useEffect(() => {
        if (authToken && authToken !== '') {
            // update playlist
            fetch('/virtual-turntable/server/playlist')
                .then((response) => {
                    if (response.ok) {
                        response.json().then((data) => {
                            setLibraryPlaylistID(data.playlistID);
                        });
                    }
                }
            );

            // update user profile
            if (hostUserID) {
                SpotifyAPI.getUserProfile(authToken, hostUserID)
                    .then((user) => {
                        setHostUserProfile(user);
                        console.log(user);
                    }
                );
            }
        }
    }, [hostUserID, authToken]);

    useEffect(() => {
        if (libraryPlaylistID) {
            SpotifyAPI.getPlaylistAlbums(authToken, libraryPlaylistID)
                .then((albums) => {
                    setLibrary(albums);
                }
            );
        }
    }, [libraryPlaylistID]);

    useEffect(() => {
        if (isHostSettingsUpdateLocal.current) {
            const settings = { ...hostSettings, volume: volume };
            WebSocketManagerInstance.send(JSON.stringify({ command: 'settings', value: settings }));
        }
    }, [volume]);

    useEffect(() => {
        isHostSettingsUpdateLocal.current = false;
        setVolume(hostSettings.volume);
    }, [hostSettings.volume]);

    function handleAlbumClick(albumID: string, controlAllowed: boolean) {
        if (controlAllowed) {
            WebSocketManagerInstance.send(JSON.stringify({ command: 'playAlbum', value: albumID }));
        }
    }

    function updateVolume(newVolume: number) {
        isHostSettingsUpdateLocal.current = true;
        setVolume(newVolume);
    }

    function handlePhoto(photo: string) {
        handleUpload(photo);
        setIsScannerOpen(false);
    }

    const isHost = hostUserProfile?.id !== undefined && userProfile?.id === hostUserProfile?.id;
    const displayName = hostUserProfile?.id !== undefined ? (isHost ? 'Your' : `${hostUserProfile?.display_name}'s`) : null;

    const controlAllowed =  hostSettings?.enableRemote && (isHost || (hostSettings?.enforceSignature === false))

    if (authToken && authToken !== '') {
        // CONTROLLER
        return (
            <>
                {/* BANNER */}
                <div className='banner'>
                    <div className='row anchorLeft'>
                        <Tooltip>
                            <TooltipTrigger>
                                <a href={userProfile?.external_urls.spotify} target='_blank' rel='noreferrer'>
                                    <img className='userImage'
                                        src={userProfile?.images?.[0]?.url || 'https://i.scdn.co/image/ab676161000051747baf6a3e4e70248079e48c5a'} alt='Your Profile'
                                        width={64}
                                    />
                                </a>
                            </TooltipTrigger>
                            <TooltipContent>{userProfile?.display_name}</TooltipContent>
                        </Tooltip>

                        { !isHost && hostUserProfile &&
                            <>
                                <img src='/virtual-turntable/icons/arrowRight.svg' alt='Using' width={32} />
                                <Tooltip>
                                    <TooltipTrigger>
                                        <a href={hostUserProfile?.external_urls?.spotify} target='_blank' rel='noreferrer'>
                                            <img className='userImage'
                                                src={hostUserProfile?.images?.[0]?.url || 'https://i.scdn.co/image/ab676161000051747baf6a3e4e70248079e48c5a'} alt="Host's Profile"
                                                width={64}
                                            />
                                        </a>
                                    </TooltipTrigger>
                                    <TooltipContent>{hostUserProfile?.display_name}</TooltipContent>
                                </Tooltip>
                            </>
                        }

                        <a href={libraryPlaylistID !== null ? `https://open.spotify.com/playlist/${libraryPlaylistID}` : ''} target='_blank' rel='noreferrer'>
                            <h1>{displayName} Virtual Turntable</h1>
                        </a>
                    </div>

                    <div className='poweredBy anchorRight'>
                        <p>Powered by</p>
                        <a href='https://www.spotify.com/' target='_blank' rel='noreferrer'>
                            <img className='brandImage'
                                src='https://storage.googleapis.com/pr-newsroom-wp/1/2023/05/Spotify_Full_Logo_RGB_Green.png' alt='Spotify Logo'
                                height={32}
                            />
                        </a>
                    </div>
                </div>

                <div className='panel'>
                    {/* SIDEBAR */}
                    { currentAlbum !== null &&
                        <div className='sidebar'>
                            {/* <h2>Your Collection</h2> */}
                            {
                                library.map((album, index) => (
                                    <div key={index} className='album'>
                                        <Tooltip placement='right'>
                                            <TooltipTrigger>
                                                <img className={`albumArtMini ${!controlAllowed && 'forbidden'}`} onClick={() => handleAlbumClick(album.id, controlAllowed)}
                                                    src={album.images[0].url} alt='Album Cover'
                                                />
                                            </TooltipTrigger>
                                            <TooltipContent>{album.name}</TooltipContent>
                                        </Tooltip>
                                    </div>
                                ))
                            }
                        </div>
                    }

                    {/* MAIN */}
                    <div className='main'>
                        {currentAlbum !== null ?
                            <div className='row'>
                                <div>
                                    <h1>{currentAlbum?.name}</h1>
                                    {currentAlbum !== null &&
                                        <a href={currentAlbum.external_urls.spotify} target='_blank' rel='noreferrer'>
                                            <img className='albumArt'
                                                src={currentAlbum.images[0].url} alt='Album Cover'
                                            />
                                        </a>
                                    }
                                    <h2>{currentTrack?.name}</h2>
                                </div>

                                {/* VOLUME BAR */}
                                <div className='column'>
                                    <img src='/virtual-turntable/icons/mute.svg' alt='-' />
                                    <input type='range' min={0} max={100}
                                        value={volume}
                                        onChange={(e) => updateVolume(parseInt(e.target.value))}
                                        orient='vertical'
                                        disabled={!controlAllowed}
                                    />
                                    <img src='/virtual-turntable/icons/volume.svg' alt='+' />
                                </div>
                            </div>
                            :
                            <div className='centre'>
                                <div className='error'>
                                    <h1>Uh, oh!</h1>
                                    <img className='errorImg' src='/virtual-turntable/vinyl-smashed.png' alt='404' height={400} />
                                    <h2>Cannot establish connection to the Virtual Turntable.</h2>
                                    <p>Please ensure the host client is running correctly:</p>
                                    <ul>
                                        <li>Check the network connection of the host device.</li>
                                        <li>Ensure the client is running on the host.</li>
                                        <li>Ensure that the host is active and connected.</li>
                                        <li>Try refreshing the page or restarting the client.</li>
                                    </ul>
                                    <p><i>Otherwise, maybe it’s time to dust off the old boombox...</i></p>
                                </div>
                            </div>
                        }

                        {/* PLAYBACK CONTROLS */}
                        {currentAlbum &&
                            <div>
                                <div className='controls'>
                                    <button onClick={() => WebSocketManagerInstance.send(JSON.stringify({command: 'playPrevious'}))}
                                        disabled={!controlAllowed}
                                    >
                                        <img src='/virtual-turntable/icons/previous.svg' alt='Previous' />
                                    </button>
                                    {/* <button
                                        onMouseDown={() => WebSocketManagerInstance.send(JSON.stringify({command: 'reverse'}))}
                                        onMouseUp={() => WebSocketManagerInstance.send(JSON.stringify({command: 'seek', value: -10}))}
                                        disabled={!controlAllowed}
                                    >
                                        <img src='/virtual-turntable/icons/rewind.svg' alt='Rewind' />
                                    </button> */}
                                    <button
                                        onClick={() => WebSocketManagerInstance.send(JSON.stringify({
                                            command: 'playState',
                                            value: isPlaying ? false : true
                                        }))}
                                        disabled={!controlAllowed}
                                    >
                                        <img src={isPlaying ? '/virtual-turntable/icons/pause.svg' : '/virtual-turntable/icons/play.svg'} alt='Play/Pause' />
                                    </button>
                                    {/* <button
                                        onMouseDown={() => WebSocketManagerInstance.send(JSON.stringify({command: 'forwards'}))}
                                        onMouseUp={() => WebSocketManagerInstance.send(JSON.stringify({command: 'seek', value: 10}))}
                                        disabled={!controlAllowed}
                                    >
                                        <img src='/virtual-turntable/icons/forwards.svg' alt='Fast Forward' />
                                    </button> */}
                                    <button onClick={() => WebSocketManagerInstance.send(JSON.stringify({command: 'playNext'}))}
                                        disabled={!controlAllowed}
                                    >
                                        <img src='/virtual-turntable/icons/next.svg' alt='Next' />
                                    </button>
                                </div>

                                <div className='controls'>
                                    <button disabled={!controlAllowed} onClick={() => setIsScannerOpen(true)}>
                                        <img src='/virtual-turntable/icons/scan.svg' alt='Scan' /> Scan Album
                                    </button>
                                </div>

                                {/* <div>
                                    <input type="file" accept="image/*" onChange={handleUpload} />
                                </div> */}
                            </div>
                        }
                    </div>

                </div>

                <Dialogue open={isScannerOpen}>
                    <DialogueContent>
                        <button onClick={() => setIsScannerOpen(false)}>Close</button>
                        <h2>Scan Album</h2>
                        <div className='camera'>
                            <WebcamCapture handlePhoto={handlePhoto} />
                        </div>
                    </DialogueContent>
                </Dialogue>
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

export default RemoteController
