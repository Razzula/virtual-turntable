import IMusicAPI from '../IMusicAPI';
import { Album, User } from '../types/Spotify';

class SpotifyAPI implements IMusicAPI {

    public async connect(authToken: string, deviceID: string): Promise<void> {
        fetch('https://api.spotify.com/v1/me/player', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({ device_ids: [deviceID] }),
        });
    }

    public async getAlbum(authToken: string, albumID: string): Promise<Album> {
        return fetch(`https://api.spotify.com/v1/albums/${albumID}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`,
            }
        }).then(response => response.json());
    }

    public async playAlbum(authToken: string, albumID: string, offset: number = 0, position_ms: number = 0): Promise<void> {
        fetch('https://api.spotify.com/v1/me/player/play', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`,
            },
            body: JSON.stringify({
                context_uri: `spotify:album:${albumID}`,
                offset: { position: offset },
                position_ms: position_ms
            }),
        });
    }

    public async playTrack(authToken: string, trackID: string, offset: number = 0, position_ms: number = 0): Promise<void> {
        fetch('https://api.spotify.com/v1/me/player/play', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`,
            },
            body: JSON.stringify({
                uris: [`spotify:track:${trackID}`],
                offset: { position: offset },
                position_ms: position_ms
            }),
        });
    }

    public async playPlaylist(authToken: string, playlistID: string, offset: number = 0, position_ms: number = 0): Promise<void> {
        fetch('https://api.spotify.com/v1/me/player/play', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`,
            },
            body: JSON.stringify({
                context_uri: `spotify:playlist:${playlistID}`,
                offset: { position: offset },
                position_ms: position_ms
            }),
        });
    }

    public async getOwnProfile(authToken: string): Promise<User> {
        return fetch('https://api.spotify.com/v1/me', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
        }).then(response => response.json());
    }

    public async getUserProfile(authToken: string, userID: string): Promise<User> {
        return fetch(`https://api.spotify.com/v1/users/${userID}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`,
            },
        }).then(response => response.json());
    }

    public async getPlaylistAlbums(authToken: string, playlistID: string): Promise<Album[]> {

        const albumsIDs: Set<string> = new Set();

        // get first batch of tracks
        let result = await fetch(`https://api.spotify.com/v1/playlists/${playlistID}/tracks`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
        }).then(response => response.json());

        // extract album IDs
        result.items.forEach((item: any) => {
            albumsIDs.add(item.track.album.id);
        });

        // repeat with pagination, if necessary
        while (result.next) {
            break;
        }

        // get album details
        const albums: Album[] = [];

        result = await fetch(`https://api.spotify.com/v1/albums?ids=${Array.from(albumsIDs).join(',')}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
        }).then(response => response.json());

        result.albums.forEach((album: Album) => {
            albums.push(album);
        });

        return albums;
    }

    public async setShuffle(authToken: string, shuffle: boolean): Promise<void> {
        const response = await fetch(`https://api.spotify.com/v1/me/player/shuffle?state=${shuffle}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`,
            },
            body: JSON.stringify({ state: shuffle }),
        });
        const text = await response.text();
        console.warn("Response status:", response.status, "body:", text);
        if (!response.ok) {
            throw new Error(`Failed to set shuffle: ${response.statusText}`);
        }
    }

}

export default new SpotifyAPI();
