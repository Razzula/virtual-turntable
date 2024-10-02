class SpotifyAPI {

    public static async setDevice(authToken: string, deviceID: string): Promise<void> {
        fetch('https://api.spotify.com/v1/me/player', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({ device_ids: [deviceID] }),
        });
    }

    public static async getAlbum(authToken: string, albumID: string): Promise<any> {
        return fetch(`https://api.spotify.com/v1/albums/${albumID}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`,
            }
        })
        .then(response => response.json());
    }

    public static async playAlbum(authToken: string, albumID: string, offset: number = 0, position_ms: number = 0): Promise<void> {
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

export default SpotifyAPI;
