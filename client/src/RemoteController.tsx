import { Album, Track, User } from './types/Spotify.ts'

import './styles/App.css'
import WebSocketManagerInstance from './WebSocketManager';
import { useEffect, useState } from 'react';
import SpotifyAPI from './Spotify/SpotifyAPI.ts';

type RemoteControllerProps = {
    authToken: string;
    userProfile: User | null;
    isPlaying: boolean;
    currentAlbum: Album | null;
    currentTrack: Track | null;
    handleFileUpload: (event: React.ChangeEvent<HTMLInputElement>) => void;
    // webSocketManagerInstance: typeof WebSocketManagerInstance;
};

function RemoteController({
    authToken,
    userProfile,
    isPlaying, currentAlbum, currentTrack,
    handleFileUpload,
    // webSocketManagerInstance,
}: RemoteControllerProps): JSX.Element {

    const [libraryPlaylistID, setLibraryPlaylistID] = useState<string | null>(null);
    const [library, setLibrary] = useState<Album[]>([]);

    const [hostUserID, setHostUserID] = useState<string | null>(null);
    const [hostUserProfile, setHostUserProfile] = useState<User | null>(null);

    useEffect(() => {
        document.body.className = 'default';
    }, []);

    useEffect(() => {
        // get host user
        fetch('/virtual-turntable/server/host')
            .then((response) => {
                if (response.ok) {
                    response.json().then((data) => {
                        setHostUserID(data.hostUserID);
                    });
                }
            }
        );
    }, []);

    useEffect(() => {
        if (authToken && authToken !== '') {
            // get VTT playlist
            fetch('/virtual-turntable/server/playlist')
                .then((response) => {
                    if (response.ok) {
                        response.json().then((data) => {
                            setLibraryPlaylistID(data.playlistID);
                        });
                    }
                }
            );
        }
    }, [authToken]);

    useEffect(() => {
        if (hostUserID && authToken) {
            SpotifyAPI.getUserProfile(authToken, hostUserID)
                .then((user) => {
                    setHostUserProfile(user);
                    console.log(user);
                }
            );
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

    const isHost = hostUserProfile?.id !== undefined && userProfile?.id === hostUserProfile?.id;
    const displayName = hostUserProfile?.id !== undefined ? (isHost ? 'Your' : `${hostUserProfile?.display_name}'s`) : null;

    if (authToken && authToken !== '') {
        // CONTROLLER
        return (
            <>
                {/* BANNER */}
                <div className='banner'>
                    <div className='row anchorLeft'>
                        <a href={userProfile?.external_urls.spotify} target='_blank' rel='noreferrer'>
                            <img className='userImage'
                                src={userProfile?.images?.[0].url || 'https://i.scdn.co/image/ab676161000051747baf6a3e4e70248079e48c5a'} alt='Your Profile'
                                width={64}
                            />
                        </a>

                        { !isHost && hostUserProfile &&
                            <a href={hostUserProfile?.external_urls?.spotify} target='_blank' rel='noreferrer'>
                                <img className='userImage'
                                    src={hostUserProfile?.images?.[0].url || 'https://i.scdn.co/image/ab676161000051747baf6a3e4e70248079e48c5a'} alt="Host's Profile"
                                    width={64}
                                />
                            </a>
                        }

                        <a href={userProfile?.external_urls?.spotify} target='_blank' rel='noreferrer'>
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
                        <div className='sidebar'
                        >
                            {/* <h2>Your Collection</h2> */}
                            {
                                library.map((album, index) => (
                                    <div key={index} className='album'>
                                        <a href='#' onClick={() => SpotifyAPI.playAlbum(authToken, album.id)}>
                                            <img className='albumArtMini'
                                                src={album.images[0].url} alt='Album Cover'
                                                // width={128} height={128}
                                            />
                                        </a>
                                        {/* <h3>{album.name}</h3> */}
                                    </div>
                                ))
                            }
                        </div>
                    }

                    {/* MAIN */}
                    <div className='main'>
                        {currentAlbum !== null ?
                            <>
                                <h1>{currentAlbum?.name}</h1>
                                {currentAlbum !== null &&
                                    <a href={currentAlbum.external_urls.spotify} target='_blank' rel='noreferrer'>
                                        <img className='albumArt'
                                            src={currentAlbum.images[0].url} alt='Album Cover'
                                        />
                                    </a>
                                }
                                <h2>{currentTrack?.name}</h2>
                            </>
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
                                    <button onClick={() => WebSocketManagerInstance.send(JSON.stringify({command: 'PREVIOUS'}))}>
                                        <img src='/virtual-turntable/icons/previous.svg' alt='Previous' />
                                    </button>
                                    <button onClick={() => WebSocketManagerInstance.send(JSON.stringify({command: isPlaying ? 'PAUSE' : 'PLAY'}))}>
                                        <img src={isPlaying ? '/virtual-turntable/icons/pause.svg' : '/virtual-turntable/icons/play.svg'} alt='Play/Pause' />
                                    </button>
                                    <button onClick={() => WebSocketManagerInstance.send(JSON.stringify({command: 'NEXT'}))}>
                                        <img src='/virtual-turntable/icons/next.svg' alt='Next' />
                                    </button>
                                </div>

                                <div className='controls'>
                                    <button>
                                        <img src='/virtual-turntable/icons/scan.svg' alt='Scan' /> Scan Album
                                    </button>
                                </div>

                                {/* <div>
                                    <input type="file" accept="image/*" onChange={handleFileUpload} />
                                </div> */}
                            </div>
                        }
                    </div>

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

export default RemoteController
