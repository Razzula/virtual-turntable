import { Album } from "./types/Spotify";

export interface IMusicAPI {

    connect(authToken: string, deviceID: string): Promise<void>;

    getAlbum(authToken: string, albumID: string): Promise<Album>;

    playAlbum(authToken: string, albumID: string, offset: number, position_ms: number): Promise<void>;

}

export default IMusicAPI;
