import IMusicAPI from '../IMusicAPI';
import { Album } from '../types/Spotify';

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
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({
                context_uri: `spotify:album:${albumID}`,
                offset: { position: offset },
                position_ms: position_ms
            }),
        });
    }

}

export default new SpotifyAPI();
